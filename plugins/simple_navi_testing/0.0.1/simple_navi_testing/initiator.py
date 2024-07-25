import asyncio
import random


class Initiator:

    def __init__(self):
        self.adaptor = None
        self.convertor_desc = None
        self.inet_addr = None
        self.is_embedded_channel = False
        self.count = None
        self.size = None
        self.period = None
        self.limit = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'convertor_desc':
                self.convertor_desc = value
            elif name == 'inet_addr':
                self.inet_addr = value
            elif name == 'is_embedded_channel':
                self.is_embedded_channel = value
            elif name == 'count':
                self.count = value
            elif name == 'size':
                self.size = value
            elif name == 'period':
                self.period = value
            elif name == 'limit':
                self.limit = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        overlooker = await self.create_overlooker(self.count * self.size * self.limit, self.period)
        await self.create_server(self.convertor_desc, self.count, self.inet_addr, self.is_embedded_channel, overlooker)
        await self.create_client(self.convertor_desc, self.count, self.size, self.inet_addr, self.is_embedded_channel)
        await self.create_gen(self.count, self.size, self.period, overlooker, self.limit)

    async def create_overlooker(self, limit, period):
        name = 'overlooker'
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'Overlooker'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        p = period * 3 if period >= 1 else 6
        body = {'params': [{'name': 'limit', 'value': limit}, {'name': 'period', 'value': p}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        return name

    async def create_server(self, convertor_desc, count, inet_addr, is_embedded_channel, overlooker):
        names = [f'tcp_server_{n:02d}' for n in range(count)]
        body = {'class_desc': {'package_name': 'simple_networking', 'class': 'TcpServer'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)
        await self.adaptor.group_ask(10, len(names),
                                     server_factory(names, convertor_desc, inet_addr, is_embedded_channel, overlooker))
        await self.adaptor.group_ask(10, len(names), lambda index: {'command': 'start', 'recipient': names[index]})

    async def create_client(self, convertor_desc, count, size, inet_addr, is_embedded_channel):
        groups = [[f'tcp_client_{m:02d}_{n:04d}' for n in range(size)] for m in range(count)]
        names = [item for sublist in groups for item in sublist]
        body = {'class_desc': {'package_name': 'simple_networking', 'class': 'TcpClient'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body))
        for index, group in enumerate(groups):
            await self.adaptor.group_ask(10, len(group),
                                         client_factory(group, convertor_desc,
                                                        inet_addr.get('host'), inet_addr.get('port')+index,
                                                        is_embedded_channel))
        await self.adaptor.group_ask(10, len(names), client_start_factory(names))

    async def create_gen(self, count, size, period, overlooker, limit):
        groups = [[f'navi_gen_{m:02d}_{n:04d}' for n in range(size)] for m in range(count)]
        names = [item for sublist in groups for item in sublist]
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'SimpleNaviGen'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body))
        for index, group in enumerate(groups):
            await self.adaptor.group_ask(10, len(group),
                                         gen_factory(group, count, size, index, period, overlooker, limit))
        for name in names:
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=name))


def server_factory(names, convertor_desc, inet_addr, is_embedded_channel, consumer):

    def get_values(index):
        body = {'params': [{'name': 'convertor_desc', 'value': convertor_desc},
                           {'name': 'host', 'value': inet_addr.get('host')},
                           {'name': 'port', 'value': inet_addr.get('port')+index},
                           {'name': 'is_embedded_channel', 'value': is_embedded_channel},
                           {'name': 'consumer', 'value': consumer},
                           ]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values


def client_factory(names, convertor_desc, host, port, is_embedded_channel):

    def get_values(index):
        body = {'params': [{'name': 'convertor_desc', 'value': convertor_desc},
                           {'name': 'host', 'value': host}, {'name': 'port', 'value': port},
                           {'name': 'is_embedded_channel', 'value': is_embedded_channel}]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values


def client_start_factory(names):

    def get_values(index):
        return {'command': 'start', 'body': None, 'recipient': names[index]}

    return get_values


def gen_factory(names, count, size, group, period, overlooker, limit):

    def get_values(index):
        code = f'000000000{group:02d}{index:04d}'
        consumer = f'tcp_client_{group:02d}_{index:04d}'
        lat = 58.0 + group * (10.0 / count)
        lon = 39.0 + index * (30.0 / size)
        body = {'params': [{'name': 'code', 'value': code}, {'name': 'lat', 'value': lat},
                           {'name': 'lon', 'value': lon}, {'name': 'period', 'value': period},
                           {'name': 'consumer', 'value': consumer}, {'name': 'overlooker', 'value': overlooker},
                           {'name': 'limit', 'value': limit}]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values
