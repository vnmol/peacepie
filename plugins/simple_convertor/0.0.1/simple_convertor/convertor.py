import enum


class SimpleConvertor:

    def __init__(self):
        self.adaptor = None
        self.mediator = None
        self.consumer = None
        self.packet = Packet(self)

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'raw_data':
            await self.raw_data(body)
        elif command == 'navi_data':
            await self.navi_data(body)
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        else:
            return False
        return True

    async def raw_data(self, data):
        body = self.packet.process(data)
        if not body:
            return
        if self.consumer:
            await self.adaptor.send(self.adaptor.get_msg('navi_data', body, recipient=self.consumer))

    async def navi_data(self, data):
        buf = self.adaptor.json_dumps(data).encode('utf-8')
        body = b'\xff\xfe' + (len(buf)).to_bytes(2, byteorder='big') + b'\x7f\xff' + buf
        await self.adaptor.send(self.adaptor.get_msg('raw_data', body, self.mediator))

    async def set_params(self, params, recipient):
        for param in params:
            if param.get('name') == 'mediator':
                self.mediator = param.get('value')
            elif param.get('name') == 'consumer':
                self.consumer = param.get('value')
        await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))


class Packet:

    class State(enum.Enum):
        MARKER = enum.auto()
        BODY = enum.auto()

    def __init__(self, parent):
        self.parent = parent
        self.state = self.State.MARKER
        self.length = 0
        self.data = b''

    def process(self, data):
        self.data += data
        while True:
            if self.state is self.State.MARKER:
                if len(self.data) < 6:
                    return
                pos = self.data.find(b'\xff\xfe')
                if pos == -1:
                    return
                self.data = self.data[pos+2:]
                if self.data[2:4] != b'\x7f\xff':
                    break
                self.length = int.from_bytes(self.data[:2], byteorder='big')
                self.data = self.data[4:]
                self.state = self.State.BODY
            if self.state is self.State.BODY:
                if len(self.data) < self.length:
                    return
                buf = self.data[:self.length]
                self.data = self.data[self.length:]
                self.state = self.State.MARKER
                self.length = 0
                res = self.parent.adaptor.json_loads(buf)
                return res
