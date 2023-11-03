import asyncio

from peacepie.control import admin, process_admin


class PrimeAdmin(admin.Admin):

    def __init__(self, host_name, process_name):
        super().__init__(None, host_name, process_name)
        self.process_admin = None

    async def pre_run(self):
        await super().pre_run()
        self.process_admin = process_admin.ProcessAdmin(self)

    async def handle(self, msg):
        if msg['command'] == 'create_process':
            asyncio.get_running_loop().create_task(self.create_process(msg))
        else:
            return await super().handle(msg)
        return True

    async def create_process(self, msg):
        await self.process_admin.create_process(msg['sender'])
