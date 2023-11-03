from peacepie.assist.serialization import Serializer


class InterQueue:

    def __init__(self, addr, writer=None):
        self.addr = addr
        self.writer = writer

    async def put(self, msg):
        self.writer.write(Serializer.serialize(msg))
        await self.writer.drain()

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.writer = None

    def __repr__(self):
        return f'{self.__class__.__name__}(addr={self.addr})'
