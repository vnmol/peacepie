
class Initiator:

    def __init__(self):
        self.adaptor = None
        self.index = None
        self.url = None
        self.convertor_desc = None
        self.inet_addr = None
        self.is_single_channel = False
        self.is_embedded_channel = False
        self.is_on_demand = False
        self.count = None
        self.size = None
        self.period = None
        self.limit = None
        self.main_overlooker = None
        self.overlooker_period = None
        self.skip_some_logging = False
        self.gens = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'prepare':
            await self.prepare(sender)
        elif command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'index':
                self.index = value
            elif name == 'extra-index-url':
                self.url = value
            elif name == 'convertor_desc':
                self.convertor_desc = value
            elif name == 'inet_addr':
                self.inet_addr = value
            elif name == 'is_single_channel':
                self.is_single_channel = value
            elif name == 'is_embedded_channel':
                self.is_embedded_channel = value
            elif name == 'is_on_demand':
                self.is_on_demand = value
            elif name == 'count':
                self.count = value
            elif name == 'size':
                self.size = value
            elif name == 'period':
                self.period = value
            elif name == 'limit':
                self.limit = value
            elif name == 'main_overlooker':
                self.main_overlooker = value
            elif name == 'overlooker_period':
                self.overlooker_period = value
            elif name == 'skip_some_logging':
                self.skip_some_logging = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def prepare(self, recipient):
        overlooker = await self.create_overlooker()
        await self.create_server(overlooker)
        clients = await self.create_clients()
        await self.create_gens(overlooker, clients)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('prepared', recipient=recipient))

    async def create_overlooker(self):
        name = f'overlooker_{self.index}'
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'Overlooker'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [
            {'name': 'main_overlooker', 'value': self.main_overlooker},
            {'name': 'overlooker_period', 'value': self.overlooker_period}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        if self.skip_some_logging:
            body = {'commands': ['tick', 'navi_data', 'packets_received']}
            await self.adaptor.send(self.adaptor.get_msg('not_log_commands_set', body, name))
        return name

    async def create_server(self, consumer):
        name = f'tcp_server_{self.index:02d}'
        class_desc = {'package_name': 'simple_networking', 'class': 'TcpServer', 'extra-index-url': self.url}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 30)
        body = {'params': [{'name': 'convertor_desc', 'value': self.convertor_desc},
                           {'name': 'host', 'value': self.inet_addr.get('host')},
                           {'name': 'port', 'value': self.inet_addr.get('port')},
                           {'name': 'is_embedded_channel', 'value': self.is_embedded_channel},
                           {'name': 'consumer', 'value': consumer}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name), 4)
        if self.skip_some_logging:
            body = {'commands': ['navi_data', 'received_from_channel', 'send_to_channel', 'sent']}
            await self.adaptor.ask(self.adaptor.get_msg('not_log_commands_set', body, name), 4)
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name), 30)

    async def create_clients(self):
        names = [f'tcp_client_{self.index:02d}_{n:04d}' for n in range(self.size)]
        class_desc = {'package_name': 'simple_networking', 'class': 'TcpClient', 'extra-index-url': self.url}
        body = {'class_desc': class_desc, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)
        await self.adaptor.group_ask(10, len(names), self.client_factory(names))
        if self.skip_some_logging:
            await self.adaptor.group_ask(10, len(names), self.client_not_log_factory(names))
        await self.adaptor.group_ask(10, len(names), self.client_start_factory(names))
        return names

    def client_factory(self, names):
        def get_values(index):
            code = None if self.is_single_channel else f'101010101{self.index:02d}{index:04d}'
            body = {'params': [{'name': 'convertor_desc', 'value': self.convertor_desc},
                               {'name': 'convertor_params', 'value': {'code': code}},
                               {'name': 'host', 'value': self.inet_addr.get('host')},
                               {'name': 'port', 'value': self.inet_addr.get('port')},
                               {'name': 'is_embedded_channel', 'value': self.is_embedded_channel},
                               {'name': 'is_on_demand', 'value': self.is_on_demand}
                               ]}
            return {'command': 'set_params', 'body': body, 'recipient': names[index]}
        return get_values

    def client_not_log_factory(self, names):
        def get_values(index):
            return {'command': 'not_log_commands_set',
                    'body': {'commands': ['navi_data',  'received_from_channel', 'send_to_channel', 'sent']},
                    'recipient': names[index]}
        return get_values

    def client_start_factory(self, names):
        def get_values(index):
            return {'command': 'start', 'body': None, 'recipient': names[index]}
        return get_values

    async def create_gens(self, overlooker, clients):
        self.gens = [f'navi_gen_{self.index:02d}_{n:04d}' for n in range(self.size)]
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'SimpleNaviGen'}, 'names': self.gens}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)
        await self.adaptor.group_ask(10, len(self.gens), self.gen_factory(clients, overlooker))
        if self.skip_some_logging:
            await self.adaptor.group_ask(10, len(self.gens), self.gen_not_log_factory())

    def gen_factory(self, clients, overlooker):
        def get_values(index):
            consumer = clients[index]
            code = f'101010101{self.index:02d}{index:04d}'
            lat = 58.0 + self.index * (10.0 / self.count)
            lon = 39.0 + index * (30.0 / self.size)
            body = {'params': [{'name': 'code', 'value': code},
                               {'name': 'lat', 'value': lat}, {'name': 'lon', 'value': lon},
                               {'name': 'period', 'value': self.period}, {'name': 'consumer', 'value': consumer},
                               {'name': 'overlooker', 'value': overlooker}, {'name': 'limit', 'value': self.limit}]}
            return {'command': 'set_params', 'body': body, 'recipient': self.gens[index]}
        return get_values

    def gen_not_log_factory(self):
        def get_values(index):
            return {'command': 'not_log_commands_set',
                    'body': {'commands': ['start', 'tick', 'send_to_channel', 'sent', 'navi_data']},
                    'recipient': self.gens[index]}
        return get_values

    async def start(self, recipient):
        await self.adaptor.group_ask(10, len(self.gens),
                                     lambda index: {'command': 'start', 'recipient': self.gens[index]})
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))
