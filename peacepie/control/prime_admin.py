import asyncio

from peacepie.assist import log_util
from peacepie.control import admin, process_admin, package_loader, delivery

PACKAGE_LOADER_COMMANDS = {'load_package'}

DELIVERY_COMMANDS = {'deliver_package', 'transfer'}


class PrimeAdmin(admin.Admin):

    def __init__(self, host_name, process_name):
        super().__init__(None, host_name, process_name)
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

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'create_process':
            asyncio.get_running_loop().create_task(self.create_process(msg))
        elif command in PACKAGE_LOADER_COMMANDS:
            await self.package_loader.queue.put(msg)
            self.logger.debug(log_util.async_sent_log(self, msg))
        elif command in DELIVERY_COMMANDS:
            msg['recipient'] = self.delivery.queue
            await self.connector.send(self, msg)
        else:
            return await super().handle(msg)
        return True

    async def create_process(self, msg):
        await self.process_admin.create_process(msg['sender'])
