from peacepie.assist.serialization import Serializer


class InterQueue:

    def __init__(self, writer):
        self.writer = writer

    async def put(self, msg):
        self.writer.write(Serializer.serialize(msg))
        await self.writer.drain()

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.writer = None
