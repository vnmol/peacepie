import enum


class SimpleConvertor:

    def __init__(self):
        self.adaptor = None
        self.mediator = None
        self.consumer = None
        self.questioner = None
        self.packet = Packet(self)

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'received_from_channel':
            await self.received_from_channel(body)
        elif command == 'send_to_channel':
            await self.send_to_channel(body, msg.get('sender'))
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        else:
            return False
        return True

    async def received_from_channel(self, data):
        packs = self.packet.process(data)
        for pack in packs:
            body = self.adaptor.json_loads(pack)
            if isinstance(body, str) and body == 'OK':
                await self.adaptor.send(self.adaptor.get_msg('sent', recipient=self.questioner))
                self.questioner = None
            else:
                if self.consumer:
                    await self.adaptor.send(self.adaptor.get_msg('navi_data', body, self.consumer, self.adaptor.name))
                await self.send('OK')

    async def send_to_channel(self, data, questioner):
        if self.questioner:
            if questioner:
                await self.adaptor.send(self.adaptor.get_msg('connection_is_busy', recipient=questioner))
            return
        self.questioner = questioner if questioner else self
        await self.send(data)

    async def send(self, data):
        buf = self.adaptor.json_dumps(data).encode('utf-8')
        body = b'\xff\xfe' + (len(buf)).to_bytes(2, byteorder='big') + b'\x7f\xff' + buf
        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', body, self.mediator))

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'mediator':
                self.mediator = value
            elif name == 'consumer':
                self.consumer = value
        if recipient:
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
        res = []
        self.data += data
        while True:
            if self.state is self.State.MARKER:
                if len(self.data) < 6:
                    break
                pos = self.data.find(b'\xff\xfe')
                if pos == -1:
                    break
                self.data = self.data[pos+2:]
                if self.data[2:4] != b'\x7f\xff':
                    continue
                self.length = int.from_bytes(self.data[:2], byteorder='big')
                self.data = self.data[4:]
                self.state = self.State.BODY
            if self.state is self.State.BODY:
                if len(self.data) < self.length:
                    break
                res.append(self.data[:self.length])
                self.data = self.data[self.length:]
                self.state = self.State.MARKER
                self.length = 0
        return res
