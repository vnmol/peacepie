import time

COUNT = 6000


class ScriptAssistant:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg.command == 'start':
            await self.start()
        else:
            return False
        return True
    
    async def start(self):
        await self.create_simple_navi_senders(COUNT)

    async def create_simple_navi_senders(self, count):
        items = [{'index': num, 'gen': f'gen_{num}', 'tcp_client': f'tcp_client_{num}'} for num in range(count)]
        await self.create_simple_navi_gens(items)
        await self.create_simple_tcp_clients(items)
        await self.start_simple_tcp_clients(items)

    async def create_simple_navi_gens(self, items):
        count = len(items)
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'requires_dist': 'simple_navi_gen', 'version': version, 'class': 'SimpleNaviGen'}
        names = [item['gen'] for item in items]
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': names})
        t = time.time()
        await self.adaptor.ask(msg)
        print('GENERATORS', time.time() - t)
        for item in items:
            num = item['index']
            code = f'{num}'
            code = '000000000000000'[:-len(code)] + code
            lat = 60
            lon = 40
            if count > 1:
                lon += 100 * num / (count - 1)
            body = {'params': [{'name': 'type', 'value': 'simple'}, {'name': 'code', 'value': code},
                               {'name': 'lat', 'value': lat}, {'name': 'lon', 'value': lon}]}
            await self.adaptor.send(self.adaptor.get_msg('set_params', body, recipient=item['gen']))

    async def create_simple_tcp_clients(self, items):
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'requires_dist': 'simple_tcp_client', 'version': version, 'class': 'SimpleTcpClient'}
        names = [item['tcp_client'] for item in items]
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': names})
        t = time.time()
        await self.adaptor.ask(msg)
        print('CLIENTS', time.time() - t)
        for item in items:
            version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
            class_desc = {'requires_dist': 'simple_convertor', 'version': version, 'class': 'SimpleConvertor'}
            body = {'params': [{'name': 'inet_addr', 'value': {'host': 'localhost', 'port': 7777}},
                               {'name': 'balancer', 'value': None},
                               {'name': 'producer', 'value': item['gen']},
                               {'name': 'is_on_demand', 'value': True},
                               {'name': 'convertor_desc', 'value': class_desc}]}
            await self.adaptor.send(self.adaptor.get_msg('set_params', body, recipient=item['tcp_client']))

    async def start_simple_tcp_clients(self, items):
        for item in items:
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=item['tcp_client']))
