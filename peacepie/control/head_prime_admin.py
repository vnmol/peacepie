import asyncio

from peacepie.assist import log_util
from peacepie.control import prime_admin, starter
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
        await starter.Starter(self.actor_admin).start()

    async def handle(self, msg):
        command = msg.get('command')
        if command in INTER_COMMANDS:
            await self.interlink.queue.put(msg)
            self.logger.debug(log_util.async_sent_log(self, msg))
        elif command == 'get_processes':
            res = [key for key in self.intralink.links.keys()]
            res.insert(0, self.adaptor.name)
            await self.adaptor.send(self.adaptor.get_msg('processes', {'list': res}, msg.get('sender')))
        else:
            return await super().handle(msg)
        return True
