import asyncio
import random


class Initiator:

    def __init__(self):
        self.adaptor = None
        self.convertor_desc = {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'}
        self.inet_addr = {'host': 'localhost', 'port': 4802}

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'start':
            await self.start(body)
        else:
            return False
        return True

    async def start(self, body):
        convertor_desc = body.get('convertor_desc')
        count = body.get('count')
        size = body.get('size')
        port = body.get('port')
        period = body.get('period')
        limit = body.get('limit')
        embedded_channel = body.get('embedded_channel')
        overlooker = await self.create_overlooker(count*size*limit, period)
        await self.create_server(convertor_desc, count, port, overlooker, embedded_channel)
        await self.create_client(convertor_desc, count, size, port, embedded_channel)
        await self.create_gen(count, size, period, overlooker, limit)

    async def create_overlooker(self, limit, period):
        name = 'overlooker'
        body = {'class_desc': {'package_name': 'simple_navi_tester', 'class': 'Overlooker'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        p = period * 3 if period >= 1 else 6
        body = {'params': [{'name': 'limit', 'value': limit}, {'name': 'period', 'value': p}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        return name

    async def create_server(self, convertor_desc, count, port, overlooker, embedded_channel):
        names = [f'tcp_server_{n:02d}' for n in range(count)]
        body = {'class_desc': {'package_name': 'simple_tcp_new', 'class': 'SimpleTcpServer'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)
        await self.adaptor.group_ask(10, len(names),
                                     server_factory(names, convertor_desc, port, overlooker, embedded_channel))
        await self.adaptor.group_ask(10, len(names), lambda index: {'command': 'start', 'recipient': names[index]})

    async def create_client(self, convertor_desc, count, size, port, embedded_channel):
        groups = [[f'tcp_client_{m:02d}_{n:04d}' for n in range(size)] for m in range(count)]
        names = [item for sublist in groups for item in sublist]
        body = {'class_desc': {'package_name': 'simple_tcp_new', 'class': 'SimpleTcpClient'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body))
        for index, group in enumerate(groups):
            await self.adaptor.group_ask(10, len(group),
                                         client_factory(group, convertor_desc,
                                                        {'host': 'localhost', 'port': port + index},
                                                        embedded_channel))
        await self.adaptor.group_ask(10, len(names), client_start_factory(names))

    async def create_gen(self, count, size, period, overlooker, limit):
        groups = [[f'navi_gen_{m:02d}_{n:04d}' for n in range(size)] for m in range(count)]
        names = [item for sublist in groups for item in sublist]
        body = {'class_desc': {'package_name': 'simple_navi_tester', 'class': 'SimpleNaviGen'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body))
        for index, group in enumerate(groups):
            await self.adaptor.group_ask(10, len(group),
                                         gen_factory(group, count, size, index, period, overlooker, limit))
        for name in names:
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=name))


def server_factory(names, convertor_desc, port, consumer, embedded_channel):

    def get_values(index):
        body = {'params': [{'name': 'convertor_desc', 'value': convertor_desc},
                           {'name': 'port', 'value': port + index},
                           {'name': 'consumer', 'value': consumer},
                           {'name': 'embedded_channel', 'value': embedded_channel}]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values


def client_factory(names, convertor_desc, inet_addr, embedded_channel):

    def get_values(index):
        body = {'params': [{'name': 'convertor_desc', 'value': convertor_desc},
                           {'name': 'inet_addr', 'value': inet_addr},
                           {'name': 'embedded_channel', 'value': embedded_channel}]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values


def client_start_factory(names):

    def get_values(index):
        return {'command': 'start', 'body': None, 'recipient': names[index]}

    return get_values


def gen_factory(names, count, size, group, period, overlooker, limit):

    def get_values(index):
        code = f'000000000{group:02d}{index:04d}'
        consumer = f'tcp_client_{group:02d}_{index:04d}.convertor'
        lat = 58.0 + group * (10.0 / count)
        lon = 39.0 + index * (30.0 / size)
        body = {'params': [{'name': 'code', 'value': code}, {'name': 'lat', 'value': lat},
                           {'name': 'lon', 'value': lon}, {'name': 'period', 'value': period},
                           {'name': 'consumer', 'value': consumer}, {'name': 'overlooker', 'value': overlooker},
                           {'name': 'limit', 'value': limit}]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values
