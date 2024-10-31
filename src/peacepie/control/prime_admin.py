import asyncio
import logging
import signal

from peacepie import loglistener
from peacepie.assist import log_util
from peacepie.control import admin, process_admin, package_loader, delivery

PACKAGE_LOADER_COMMANDS = {'load_package'}

DELIVERY_COMMANDS = {'deliver_package', 'transfer'}


class PrimeAdmin(admin.Admin):

    def __init__(self, host_name, process_name):
        super().__init__(None, host_name, process_name, loglistener.instance.get_log_desc())
        self.process_admin = None
        self.package_loader = None
        self.delivery = None

    async def pre_run(self):
        await super().pre_run()
        self.process_admin = process_admin.ProcessAdmin(self)
        self.package_loader = package_loader.PackageLoader(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.package_loader.run(queue))
        await queue.get()
        self.delivery = delivery.Delivery(self)
        asyncio.get_running_loop().create_task(self.delivery.run())
        loop = asyncio.get_running_loop()
        for signal_name in {'SIGINT', 'SIGTERM'}:
            loop.add_signal_handler(
                getattr(signal, signal_name),
                lambda: asyncio.create_task(self.finalize())
            )

    async def exit(self):
        await super().exit()
        await self.process_admin.exit()

    async def handle(self, msg):
        command = msg.get('command')
        sender = msg.get('sender')
        if command == 'create_process':
            await self.create_process(sender)
        elif command == 'remove_process':
            await self.remove_process(msg)
        elif command in PACKAGE_LOADER_COMMANDS:
            await self.package_loader.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        elif command in DELIVERY_COMMANDS:
            msg['recipient'] = self.delivery.queue
            await self.adaptor.send(self, msg)
        elif command == 'get_members':
            await self.get_members(msg)
        else:
            return await super().handle(msg)
        return True

    async def create_process(self, recipient):
        asyncio.get_running_loop().create_task(self.process_admin.create_process(recipient))

    async def remove_process(self, msg):
        asyncio.get_running_loop().create_task(self.process_admin.remove_process(msg))

    async def get_members(self, msg):
        body = msg.get('body')
        page_size = body.get('page_size')
        level = body.get('level') if body.get('level') else 'prime'
        xid = body.get('id') if body.get('id') else ''
        page = int(xid.split('_')[2]) if xid.startswith('_page_') else 0
        members = []
        back = self.adaptor.name
        if level == 'process':
            members = self.process_admin.get_members()
            members = [{'next_level': 'actors', 'recipient': member, 'id': member} for member in members]
            back = self.adaptor.get_head_name()
        elif level == 'actors':
            members = self.actor_admin.get_members()
            members = [{'next_level': 'actor', 'recipient': self.adaptor.name, 'id': member} for member in members]
        elif level == 'actor':
            members = [{'next_level': None, 'recipient': None, 'id': body.get('id')}]
        body = admin.format_members(level, self.adaptor.name, page_size, page, members)
        body['_back'] = {'next_level': admin.get_prev(level), 'recipient': back, 'id': '_back'}
        body['level'] = level
        ans = self.adaptor.get_msg('members', body, msg.get('sender'))
        await self.adaptor.send(ans)
