import math
import random
import time


class SimpleNaviGen:

    def __init__(self):
        self.adaptor = None
        self.period = 4
        self.t = 0
        self.code = None
        self.lat = None
        self.lon = None
        self.consumer = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'tick':
            await self.tick()
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def tick(self):
        lat = self.lat * (1 + 0.0001 * self.t * math.sin(self.t))
        lon = self.lon * (1 + 0.0001 * self.t * math.cos(self.t))
        self.t += 0.1
        data = {'id': self.adaptor.series_next('navi_id'), 'type': None, 'code': self.code, 'is_proprietary': False,
                'navi': {'time': time.time(), 'lat': lat, 'lon': lon}}
        await self.adaptor.ask(self.adaptor.get_msg('navi_send', data, recipient=self.consumer))

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'code':
                self.code = value
            elif name == 'lat':
                self.lat = value
            elif name == 'lon':
                self.lon = value
            elif name == 'consumer':
                self.consumer = value
            elif name == 'period':
                self.period = value + random.random()
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        self.adaptor.add_ticker(self.period)
