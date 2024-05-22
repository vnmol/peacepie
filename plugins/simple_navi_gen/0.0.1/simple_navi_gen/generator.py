import asyncio
import math
import random
import time

pid = 0


class SimpleNaviGen:

    def __init__(self):
        self.adaptor = None
        self.id = 0
        self.period = 4
        self.t = 0
        self.type = None
        self.code = None
        self.lat = None
        self.lon = None
        self.consumer = None
        self.router = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'tick':
            await self.send()
        elif command == 'navi_data':
            self.navi_data(body)
        elif command == 'set_params':
            self.set_params(body.get('params'))
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def send(self):
        global pid
        lat = self.lat * (1 + 0.0001 * self.t * math.sin(self.t))
        lon = self.lon * (1 + 0.0001 * self.t * math.cos(self.t))
        self.t += 0.1
        self.id = pid
        data = {'id': pid, 'key': {'type': self.type, 'code': self.code}, 'is_proprietary': False,
                'navi': {'time': time.time(), 'lat': lat, 'lon': lon}}
        pid += 1
        await self.adaptor.send(self.adaptor.get_msg('navi_data', data, recipient=self.consumer))

    def navi_data(self, data):
        if data['id'] != self.id:
            warning = f'Packet number {data["id"]} was received, number {self.id} was expected'
            self.adaptor.logger.warning(warning)
            print(warning)

    def set_params(self, params):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'router':
                self.router = value
            elif name == 'type':
                self.type = value
            elif name == 'code':
                self.code = value
            elif name == 'lat':
                self.lat = value
            elif name == 'lon':
                self.lon = value
            elif name == 'consumer':
                self.consumer = value

    async def start(self):
        await asyncio.sleep(random.randrange(10))
        self.adaptor.add_ticker(self.period)
