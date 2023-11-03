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
        if msg.command == 'tick':
            await self.send()
        elif msg.command == 'navi_data':
            self.navi_data(msg.body)
        elif msg.command == 'set_params':
            self.set_params(msg.body['params'])
        elif msg.command == 'start':
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
            if param['name'] == 'router':
                self.router = param['value']
            elif param['name'] == 'type':
                self.type = param['value']
            elif param['name'] == 'code':
                self.code = param['value']
            elif param['name'] == 'lat':
                self.lat = param['value']
            elif param['name'] == 'lon':
                self.lon = param['value']
            elif param['name'] == 'consumer':
                self.adaptor.add_to_cache(param['value']['node'], param['value']['entity'])
                self.consumer = param['value']['entity']

    async def start(self):
        '''
        key = {'type': self.type, 'code': self.code}
        subscriber = {'node': self.adaptor.get_node(), 'entity': self.adaptor.name}
        body = {'key': key, 'subscriber': subscriber}
        await self.adaptor.ask(self.adaptor.get_msg('subscribe', body, recipient=self.router))
        '''
        await asyncio.sleep(random.randrange(10))
        self.adaptor.add_ticker(self.period)
