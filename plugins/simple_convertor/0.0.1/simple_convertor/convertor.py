import enum
import sys

admin = sys.modules['peacepie.control.admin']


class SimpleConvertor:

    def __init__(self):
        self.adaptor = None
        self.mediator = None
        self.consumer = None
        self.packet = Packet(self)

    async def handle(self, msg):
        command = msg['command']
        if command == 'raw_data':
            await self.raw_data(msg['body'])
        elif command == 'navi_data':
            await self.navi_data(msg['body'])
        elif command == 'set_params':
            await self.set_params(msg)
        else:
            return False
        return True

    async def raw_data(self, data):
        global admin
        body = self.packet.process(data)
        if not body:
            return
        admin.received += 1
        if self.consumer:
            await self.adaptor.send(self.adaptor.get_msg('navi_data', body, recipient=self.consumer))

    async def navi_data(self, data):
        buf = self.adaptor.json_dumps(data).encode('utf-8')
        body = b'\xff\xfe' + (len(buf)).to_bytes(2, byteorder='big') + b'\x7f\xff' + buf
        await self.adaptor.send(self.adaptor.get_msg('raw_data', body, self.mediator))

    async def set_params(self, msg):
        for param in msg['body']['params']:
            if param['name'] == 'mediator':
                if type(param['value']) is dict:
                    self.adaptor.add_to_cache(param['value']['node'], param['value']['entity'])
                    name = param['value']['entity']
                else:
                    name = param['value']
                self.mediator = name
            elif param['name'] == 'consumer':
                if type(param['value']) is dict:
                    self.adaptor.add_to_cache(param['value']['node'], param['value']['entity'])
                    self.consumer = param['value']['entity']
                else:
                    self.consumer = param['value']
        await self.adaptor.send(self.adaptor.get_msg('params_is_set', recipient=msg['sender']))


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
