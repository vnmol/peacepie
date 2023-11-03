import asyncio


class ScriptInitiator:

    def __init__(self):
        self.adaptor = None
        self.router = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.simple_tcp_server()
        process_name_0 = await self.create_process()
        #process_name_1 = await self.create_process()
        # process_name = None
        asyncio.get_running_loop().create_task(self.create_navi_senders(process_name_0))
        #asyncio.get_running_loop().create_task(self.create_navi_senders(process_name_1))
        '''
        await self.balancer()
        await self.navi_router()
        await self.simple_tcp_server()
        t0 = time.time()
        await self.create_simple_navi_senders(COUNT)
        '''

    async def create_process(self):
        res = None
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'))
        if ans['command'] == 'process_is_created':
            res = ans['body']
        return res

    async def create_navi_senders(self, process_name):
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'script_initiator', 'version': version, 'class': 'ScriptTester'}
        addr = {'node': process_name, 'entity': None}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'tester'}, addr)
        ans = await self.adaptor.ask(msg, 2)
        if ans['command'] != 'actor_is_created':
            return
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=ans['body']))

    async def balancer(self):
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'simple_balancer', 'version': version, 'class': 'Balancer'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'balancer'})
        await self.adaptor.ask(msg)

    async def navi_router(self):
        name = 'navi_router'
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'simple_navi_router', 'version': version, 'class': 'SimpleNaviRouter'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': name})
        answer = await self.adaptor.ask(msg)
        if answer.command != 'actor_is_created':
            return
        self.router = {'node': answer.body, 'entity': name}

    async def simple_tcp_server(self):
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'simple_tcp_server', 'version': version, 'class': 'SimpleTcpServer'}
        body = {'class_desc': class_desc, 'name': 'tcp_server_7777'}
        msg = self.adaptor.get_msg('create_actor', body)
        await self.adaptor.ask(msg)
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'simple_convertor', 'version': version, 'class': 'SimpleConvertor'}
        body = {'params': [{'name': 'port', 'value': 7777},
                           {'name': 'convertor_desc', 'value': class_desc},
                           {'name': 'embedded_channel', 'value': True},
                           {'name': 'router', 'value': self.router}]}
        msg = self.adaptor.get_msg('set_params', body, recipient='tcp_server_7777')
        await self.adaptor.send(msg)
        await self.adaptor.send(self.adaptor.get_msg('start', recipient='tcp_server_7777'))

    async def create_simple_navi_senders(self, count):
        items = [{'index': num, 'gen': f'gen_{num}', 'tcp_client': f'tcp_client_{num}'} for num in range(count)]
        await self.create_simple_navi_gens(items)
        await self.create_simple_tcp_clients(items)
        await self.start_simple_tcp_clients(items)

    async def create_simple_navi_gens(self, items):
        count = len(items)
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'simple_navi_gen', 'version': version, 'class': 'SimpleNaviGen'}
        names = [item['gen'] for item in items]
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': names})
        await self.adaptor.ask(msg)
        for item in items:
            num = item['index']
            code = f'{num}'
            code = '000000000000000'[:-len(code)] + code
            lat = 60
            lon = 40
            if count > 1:
                lon += 100 * num / (count - 1)
            body = {'params': [{'name': 'type', 'value': 'simple'}, {'name': 'code', 'value': code},
                               {'name': 'lat', 'value': lat}, {'name': 'lon', 'value': lon},
                               {'name': 'router', 'value': self.router}]}
            await self.adaptor.send(self.adaptor.get_msg('set_params', body, recipient=item['gen']))

    async def create_simple_tcp_clients(self, items):
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'simple_tcp_client', 'version': version, 'class': 'SimpleTcpClient'}
        names = [item['tcp_client'] for item in items]
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': names})
        await self.adaptor.ask(msg)
        for item in items:
            version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
            class_desc = {'package_name': 'simple_convertor', 'version': version, 'class': 'SimpleConvertor'}
            body = {'params': [{'name': 'inet_addr', 'value': {'host': 'localhost', 'port': 7777}},
                               {'name': 'balancer', 'value': None},
                               {'name': 'producer', 'value': item['gen']},
                               {'name': 'is_on_demand', 'value': True},
                               {'name': 'convertor_desc', 'value': class_desc}]}
            await self.adaptor.send(self.adaptor.get_msg('set_params', body, recipient=item['tcp_client']))

    async def start_simple_tcp_clients(self, items):
        for item in items:
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=item['tcp_client']))
