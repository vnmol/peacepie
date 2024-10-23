import asyncio
import logging

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

    async def pre_run(self):
        await super().pre_run()
        self.safe_admin = safe_admin.SafeAdmin(self)
        self.interlink = inter_server.InterServer(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.interlink.run(queue))
        await queue.get()
        class_desc = {'package_name': 'peacepie.control.internal_starter', 'class': 'InternalStarter', 'internal': True}
        body = {'class_desc': class_desc, 'name': 'internal_starter'}
        msg = self.adaptor.get_msg('create_actor', body, sender=self.adaptor.get_self_addr())
        await self.adaptor.send(msg)

    async def exit(self):
        await super().exit()
        await self.interlink.exit()
        loglistener.instance.stop()
        logging.info(log_util.get_alias(self.parent) + ' is stopped')

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
        elif command == 'change_caches':
            await self.change_caches(msg)
        elif command == 'get_members':
            await self.get_members(msg)
        elif command == 'test_error':
            self.parent.set_test_error(msg.get('body'))
        else:
            return await super().handle(msg)
        return True

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
