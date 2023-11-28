import asyncio
import logging


class ClientLink:

    def __init__(self, link_host, link_port, serializer):
        self.logger = logging.getLogger()
        self.serializer = serializer
        self.link_host = link_host
        self.link_port = link_port
        self.reader = None
        self.writer = None
        self.queue = None

    async def start_client(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.link_host, self.link_port)
            self.logger.info(f' Channel ({self.link_host}, {self.link_port}) is opened')
        except Exception as ex:
            self.logger.exception(ex)
        await self.client_handle()

    async def client_handle(self):
        while self.reader:
            if self.reader.at_eof():
                break
            try:
                data = await self.reader.read(255)
                res = self.serializer.deserialize(data)
                if res:
                    await self.handle(res)
            except Exception as ex:
                self.logger.exception(ex)

    async def handle(self, msg):
        if self.queue:
            await self.queue.put(msg)

    async def send(self, msg):
        data = self.serializer.__class__.serialize(msg)
        self.writer.write(data)
        await self.writer.drain()

    async def ask(self, msg, timeout=1):
        self.queue = asyncio.Queue()
        await self.send(msg)
        asyncio.get_running_loop().create_task(self.wait(timeout))
        ans = await self.queue.get()
        return ans

    async def wait(self, timeout):
        await asyncio.sleep(timeout)
        await self.queue.put(None)
