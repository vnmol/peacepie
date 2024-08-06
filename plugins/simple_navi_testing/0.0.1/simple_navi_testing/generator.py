import math
import random
import time


class SimpleNaviGen:

    def __init__(self):
        self.adaptor = None
        self.period = 1
        self.t = 0
        self.code = None
        self.lat = None
        self.lon = None
        self.consumer = None
        self.overlooker = None
        self.ticker = None
        self.limit = 0
        self.sent = 0

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'tick':
            await self.tick()
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start(msg.get('sender'))
        else:
            return False
        return True

    async def tick(self):
        lat = self.lat * (1 + 0.0001 * self.t * math.sin(self.t))
        lon = self.lon * (1 + 0.0001 * self.t * math.cos(self.t))
        self.t += 0.1
        data = {'id': self.adaptor.series_next('navi_id'), 'type': None, 'code': self.code, 'is_proprietary': False,
                'navi': {'time': time.time(), 'lat': lat, 'lon': lon}}
        await self.adaptor.ask(self.adaptor.get_msg('send_to_channel', data, self.consumer))
        await self.adaptor.send(self.adaptor.get_msg('navi_data', data, self.overlooker, self.adaptor.name))
        self.sent += 1
        if self.sent == self.limit:
            self.adaptor.remove_ticker(self.ticker)

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
                self.period = value  # * (1 + random.random())
            elif name == 'overlooker':
                self.overlooker = value
            elif name == 'limit':
                self.limit = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        self.ticker = self.adaptor.add_ticker(self.period)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))
