class Major:

    def __init__(self):
        self.adaptor = None
        self.major_timeout = None
        self.junior_count = None
        self.junior_period = None
        self.junior_flags = None
        self.gen_count = None
        self.gen_period = None
        self.gen_limit = None
        self.does_gen_ask = False
        self.skip_some_logging = False
        self.beat_count = 0

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start()
        elif command == 'timer':
            await self.timer()
        elif command == 'extra_beat':
            await self.extra_beat()
        else:
            return False
        return True


    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        query = self.adaptor.get_msg('create_process')
        nodes = [(await self.adaptor.ask(query, timeout=4)).get('body').get('node')
                 for _ in range(self.junior_count - 1)]
        nodes.insert(0, self.adaptor.get_node())
        names = [f'junior_{i}' for i in range(len(nodes))]
        class_desc = {'requires_dist': 'simple_actor_recreate_testing', 'class': 'Junior'}
        await self.adaptor.group_ask(
            10, len(names), lambda index: {'command': 'create_actor',
                                           'body': {'class_desc': class_desc, 'name': names[index]},
                                           'recipient': nodes[index]})
        await self.adaptor.group_ask(10, len(names), self.junior_params_factory(names, nodes))
        for name in names:
            await self.adaptor.send(self.adaptor.get_msg('start', None, name))
        self.adaptor.start_timer(self.major_timeout)

    def junior_params_factory(self, names, nodes):
        def get_values(index):
            body = {'params': [
                {'name': 'major', 'value': self.adaptor.name},
                {'name': 'index', 'value': index},
                {'name': 'junior_count', 'value': self.junior_count},
                {'name': 'junior_period', 'value': self.junior_period},
                {'name': 'junior_flags', 'value': self.junior_flags},
                {'name': 'gen_count', 'value': self.gen_count},
                {'name': 'gen_period', 'value': self.gen_period},
                {'name': 'gen_limit', 'value': self.gen_limit},
                {'name': 'does_gen_ask', 'value': self.does_gen_ask},
                {'name': 'skip_some_logging', 'value': self.skip_some_logging},
                {'name': 'nodes', 'value': nodes}
            ]}
            return {'command': 'set_params', 'body': body, 'recipient': names[index]}
        return get_values

    async def timer(self):
        pass
        # await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}))
        # await self.adaptor.send(self.adaptor.get_msg('exit', None))

    async def extra_beat(self):
        self.beat_count += 1
        print('EXTRA_BEAT', self.beat_count, self.junior_count, self.adaptor.get_caller_info())
        if self.beat_count == self.junior_count:
            print(self.adaptor.get_current_time_string(), self.adaptor.get_caller_info())
            # await self.adaptor.send(self.adaptor.get_msg('exit', None, self.adaptor.get_head_addr()))
