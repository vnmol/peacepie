class MainInitiator:

    def __init__(self):
        self.adaptor = None
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
        self.timeout = None
        self.overlooker_period = 4
        self.skip_some_logging = False
        self.is_testing = False

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
            if name == 'extra-index-url':
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
            elif name == 'timeout':
                self.timeout = value
            elif name == 'overlooker_period':
                self.overlooker_period = value
            elif name == 'skip_some_logging':
                self.skip_some_logging = value
            elif name == 'is_testing':
                self.is_testing = value
        self.convertor_desc['extra-index-url'] = self.url
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        main_overlooker = await self.create_main_overlooker()
        processes = await self.create_processes()
        await self.create_initiators(main_overlooker, processes)

    async def create_main_overlooker(self):
        overall_limit = self.count * self.size * self.limit if self.limit else self.limit
        name = 'main_overlooker'
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'MainOverlooker'}, 'name': name}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [{'name': 'limit', 'value': overall_limit},
                           {'name': 'timeout', 'value': self.timeout},
                           {'name': 'overlooker_period', 'value': self.overlooker_period},
                           {'name': 'is_testing', 'value': self.is_testing}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        if self.skip_some_logging:
            body = {'commands': ['tick', 'navi_data', 'packets_received']}
            msg = self.adaptor.get_msg('not_log_commands_set', body, name)
            await self.adaptor.send(msg)
        return ans.get('body')

    async def create_processes(self):
        res = [None]
        for i in range(self.count - 1):
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'))
            res.append(ans.get('body'))
        return res

    async def create_initiators(self, main_overlooker, processes):
        names = [f'initiator_{index}' for index in range(len(processes))]
        await self.adaptor.group_ask(30, len(names), self.initiator_create_factory(processes, names))
        await self.adaptor.group_ask(30, len(names), self.initiator_set_params_factory(names, main_overlooker))
        await self.adaptor.group_ask(30, len(names), lambda index: {'command': 'prepare', 'recipient': names[index]})
        await self.adaptor.group_ask(30, len(names), lambda index: {'command': 'start', 'recipient': names[index]})
        await self.adaptor.send(self.adaptor.get_msg('start', None, main_overlooker))

    def initiator_create_factory(self, processes, names):
        class_desc = {'package_name': 'simple_navi_testing', 'class': 'Initiator'}

        def get_values(index):
            body = {'class_desc': class_desc, 'name': names[index]}
            return {'command': 'create_actor', 'body': body, 'recipient': processes[index]}

        return get_values

    def initiator_set_params_factory(self, names, main_overlooker):
        host = self.inet_addr.get('host')
        port = self.inet_addr.get('port')

        def get_values(index):
            body = {'params': [
                {'name': 'index', 'value': index},
                {'name': 'extra-index-url', 'value': self.url},
                {'name': 'convertor_desc', 'value': self.convertor_desc},
                {'name': 'inet_addr', 'value': {'host': host, 'port': port+index}},
                {'name': 'is_single_channel', 'value': self.is_single_channel},
                {'name': 'is_embedded_channel', 'value': self.is_embedded_channel},
                {'name': 'is_on_demand', 'value': self.is_on_demand},
                {'name': 'count', 'value': self.count},
                {'name': 'size', 'value': self.size},
                {'name': 'period', 'value': self.period},
                {'name': 'limit', 'value': self.limit},
                {'name': 'main_overlooker', 'value': main_overlooker},
                {'name': 'overlooker_period', 'value': self.overlooker_period},
                {'name': 'skip_some_logging', 'value': self.skip_some_logging}
            ]}
            return {'command': 'set_params', 'body': body, 'recipient': names[index]}

        return get_values

