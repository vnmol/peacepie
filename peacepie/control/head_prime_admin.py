import asyncio
import logging

from peacepie.assist import log_util
from peacepie.control import prime_admin, admin
from peacepie.control.inter import inter_server

INTER_COMMANDS = {'inter_connect', 'inter_disconnect'}


class HeadPrimeAdmin(prime_admin.PrimeAdmin):

    def __init__(self, host_name, process_name):
        super().__init__(host_name, process_name)
        self.is_head = True
        self.interlink = None

    async def pre_run(self):
        await super().pre_run()
        self.interlink = inter_server.InterServer(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.interlink.run(queue))
        await queue.get()
        class_desc = {'package_name': 'peacepie.control.starter', 'class': 'Starter', 'internal': True}
        body = {'class_desc': class_desc, 'name': 'internal_starter'}
        msg = self.adaptor.get_msg('create_actor', body, sender=self.adaptor.get_self_addr())
        await self.adaptor.send(msg)
        # await starter.Starter(self.actor_admin).start()

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
            self.logger.debug(log_util.async_sent_log(self, msg))
        elif command == 'get_members':
            await self.get_members(msg)
        else:
            return await super().handle(msg)
        return True

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
