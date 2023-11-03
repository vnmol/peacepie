import asyncio
import math
import sys
import time

pid = 0

admin = sys.modules['peacepie.control.admin']


class TcpClients:

    def __init__(self):
        self.adaptor = None
        self.count = 10
        self.period = 1
        self.inet_addr = {'host': 'localhost', 'port': 7777}
        self.producers = [None for _ in range(self.count)]
        self.selector = 0

    async def handle(self, msg):
        command = msg['command']
        if command == 'tick':
            await self.tick()
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        for i in range(self.count):
            code = f'{i}'
            code = '000000000000000'[:-len(code)] + code
            lat = 60.0
            lon = 40.0
            if self.count > 1:
                lon += 100 * i / (self.count - 1)
            self.producers[i] = Producer(self, code, lat, lon)
        self.adaptor.add_ticker(self.period / self.count)

    async def tick(self):
        await self.producers[self.selector].send()
        self.selector += 1
        if self.selector == self.count:
            self.selector = 0


class Producer:

    def __init__(self, parent, code, lat, lon):
        self.parent = parent
        self.code = code
        self.lat = lat
        self.lon = lon
        self.t = 0
        self.reader = None
        self.writer = None

    async def send(self):
        global admin
        if not self.writer:
            await self.connect()
        if not self.writer:
            return
        buf = self.parent.adaptor.json_dumps(self.get_navi_data()).encode('utf-8')
        body = b'\xff\xfe' + (len(buf)).to_bytes(2, byteorder='big') + b'\x7f\xff' + buf
        self.writer.write(body)
        await self.writer.drain()
        admin.sent += 1

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.parent.inet_addr['host'], self.parent.inet_addr['port'])
        except Exception as e:
            self.parent.adaptor.loggerlogger.exception(e)

    def get_navi_data(self):
        global pid
        lat = self.lat * (1 + 0.0001 * self.t * math.sin(self.t))
        lon = self.lon * (1 + 0.0001 * self.t * math.cos(self.t))
        self.t += 0.1
        res = {'id': pid, 'key': {'type': 'simple', 'code': self.code}, 'is_proprietary': False,
               'navi': {'time': time.time(), 'lat': lat, 'lon': lon}}
        pid += 1
        return res
