import asyncio
import logging
import signal

from peacepie import loglistener
from peacepie.assist import log_util
from peacepie.control import prime_admin, admin, safe_admin
from peacepie.control.inter import inter_server

INTER_COMMANDS = {'inter_connect', 'inter_disconnect'}


class HeadPrimeAdmin(prime_admin.PrimeAdmin):

    def __init__(self, parent, host_name, process_name):
        super().__init__(host_name, process_name)
        self.parent = parent
        self.is_head = True
        self.interlink = None
        self.safe_admin = None
        self.registered_handlers = {}

    async def pre_run(self):
        await super().pre_run()
        self.safe_admin = safe_admin.SafeAdmin(self)
        self.interlink = inter_server.InterServer(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.interlink.run(queue))
        await queue.get()
        class_desc = {'requires_dist': 'peacepie.control.internal_starter'}
        body = {'class_desc': class_desc, 'name': 'internal_starter'}
        msg = self.adaptor.get_msg('create_actor', body, sender=self.adaptor.get_self_addr())
        self.signals_check()
        await self.adaptor.send(msg)

    async def quit(self, is_command):
        if self.adaptor.stop_event is not None:
            return
        if is_command:
            await self.process_admin.exit()
        self.adaptor.pause()
        self.adaptor.resume(True)

    async def exit(self):
        await self.finalize()
        await self.intralink.exit()
        await self.interlink.exit()
        loglistener.instance.stop()

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'actor_is_created':
            body = msg.get('body')
            if not body:
                return False
            if body.get('entity') != 'internal_starter':
                return False
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=body))
        elif command in INTER_COMMANDS:
            await self.interlink.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        elif command == 'get_credentials':
            await self.safe_admin.handle(msg)
        elif command == 'signals_check':
            self.signals_check()
        elif command == 'change_caches':
            await self.change_caches(msg)
        elif command == 'remove_from_caches':
            await self.remove_from_caches(msg)
        elif command == 'get_members':
            await self.get_members(msg)
        elif command == 'test_error':
            self.parent.set_test_error(msg.get('body'))
        else:
            return await super().handle(msg)
        return True

    def signals_check(self):
        for signal_name in {'SIGINT', 'SIGTERM'}:
            sig = getattr(signal, signal_name)
            handler = signal.getsignal(sig)
            if self.registered_handlers.get(sig) == handler:
                continue
            handler = lambda signum, frame: asyncio.create_task(self.quit(False))
            signal.signal(sig, handler)
            handler = signal.getsignal(sig)
            self.registered_handlers[sig] = handler

    async def change_caches(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        await self.add_to_cache(body.get('node'), [body.get('entity')], True)
        links = [link for link in self.intralink.links]
        await self.adaptor.group_ask(10, len(links),
                                     lambda index: {'command': 'change_cache', 'body': body,
                                                    'recipient': {'node': links[index], 'entity': None}}
        )
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('caches_are_changed', None, recipient))

    async def remove_from_caches(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        await self.remove_from_cache(body, None)
        links = [link for link in self.intralink.links]
        await self.adaptor.group_ask(10, len(links),
                                     lambda index: {'command': 'remove_from_cache', 'body': body,
                                                    'recipient': {'node': links[index], 'entity': None}}
        )
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('removed_from_caches', None, recipient))

    async def get_members(self, msg):
        body = msg.get('body')
        page_size = body.get('page_size')
        level = body.get('level') if body.get('level') else 'prime'
        xid = body.get('id') if body.get('id') else ''
        page = int(xid.split('_')[2]) if xid.startswith('_page_') else 0
        members = []
        if level == 'prime':
            members = self.intralink.get_members()
            members = [{'next_level': 'process', 'recipient': member, 'id': member} for member in members]
        elif level == 'process':
            members = self.process_admin.get_members()
            members = [{'next_level': 'actors', 'recipient': member, 'id': member} for member in members]
        elif level == 'actors':
            members = self.actor_admin.get_members()
            members = [{'next_level': 'actor', 'recipient': self.adaptor.name, 'id': member} for member in members]
        elif level == 'actor':
            members = [{'next_level': None, 'recipient': None, 'id': body.get('id')}]
        body = admin.format_members(level, self.adaptor.name, page_size, page, members)
        if level != 'prime':
            body['_back'] = {'next_level': admin.get_prev(level), 'recipient': self.adaptor.name, 'id': '_back'}
        body['level'] = level
        ans = self.adaptor.get_msg('members', body, msg.get('sender'))
        await self.adaptor.send(ans)
