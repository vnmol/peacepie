from peacepie.assist.serialization import Serializer


class IntraQueue:

    def __init__(self, lord, addr, writer):
        self.lord = lord
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
        res = f'{self.__class__.__name__}(lord={self.lord}, addr={self.addr}, '
        res += f'writer={self.writer.__class__.__name__}({id(self.writer)}))'
        return res
