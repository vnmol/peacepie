import enum

from peacepie.assist import json_util


class Serializer:

    class State(enum.Enum):
        MARKER = enum.auto()
        BODY = enum.auto()

    def __init__(self):
        self.state = self.State.MARKER
        self.length = 0
        self.data = b''

    @staticmethod
    def serialize(data):
        buf = json_util.json_dumps(data).encode('utf-8')
        return b'\xff\xfe' + (len(buf)).to_bytes(2, byteorder='big') + b'\x7f\xff' + buf

    def deserialize(self, data):
        self.data += data
        messages = []
        while True:
            if self.state is self.State.MARKER:
                if len(self.data) < 6:
                    break
                pos = self.data.find(b'\xff\xfe')
                if pos == -1:
                    break
                self.data = self.data[pos + 2:]
                if self.data[2:4] != b'\x7f\xff':
                    break
                self.length = int.from_bytes(self.data[:2], byteorder='big')
                self.data = self.data[4:]
                self.state = self.State.BODY
            if self.state is self.State.BODY:
                if len(self.data) < self.length:
                    break
                buf = self.data[:self.length]
                self.data = self.data[self.length:]
                self.state = self.State.MARKER
                self.length = 0
                res = json_util.json_loads(buf)
                messages.append(res)
        return messages if messages else None
