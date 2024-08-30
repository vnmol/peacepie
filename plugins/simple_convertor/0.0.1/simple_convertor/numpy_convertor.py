import enum
import time

import numpy

total = 0
packet = 0
details = 0


class NumpyConvertor:

    def __init__(self):
        self.adaptor = None
        self.mediator = None
        self.consumer = None
        self.questioner = None
        self.packet = Packet(self)

    async def exit(self):
        global total
        global packet
        global details
        if total:
            print(f'TOTAL={total}, packet={packet}, details={details}')
            total = None

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
        global total
        global packet
        t = time.time()
        body = self.packet.process(data)
        packet += time.time() - t
        if not body:
            return
        if isinstance(body, str) and body == 'OK':
            t1 = time.time()
            await self.adaptor.send(self.adaptor.get_msg('sent', recipient=self.questioner))
            t1 = time.time() - t1
            self.questioner = None
        else:
            t1 = time.time()
            if self.consumer:
                await self.adaptor.send(self.adaptor.get_msg('navi_data', body, self.consumer, self.adaptor.name))
            await self.send('OK')
            t1 = time.time() - t1
        total += time.time() - t - t1

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
        self.data = numpy.array([], dtype=numpy.uint8)

    def process(self, data):
        global details
        t = time.time()
        ndata = numpy.frombuffer(data, dtype=numpy.uint8)
        details += time.time() - t
        self.data = numpy.concatenate((self.data, ndata))
        while True:
            if self.state is self.State.MARKER:
                if len(self.data) < 6:
                    return
                pos = self.pos(b'\xff\xfe')
                if pos == -1:
                    return
                self.data = self.data[pos+2:]
                if not numpy.array_equal(self.data[2:4], numpy.frombuffer(b'\x7f\xff', dtype=numpy.uint8)):
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
                res = self.parent.adaptor.json_loads(buf.tobytes())
                return res

    def pos(self, pattern):
        sequence = numpy.frombuffer(pattern, dtype=numpy.uint8)
        seq_len = len(sequence)
        arr_len = len(self.data)
        if seq_len == 0 or seq_len > arr_len:
            return -1
        for i in range(arr_len - seq_len + 1):
            if numpy.array_equal(self.data[i:i + seq_len], sequence):
                return i
        return -1
