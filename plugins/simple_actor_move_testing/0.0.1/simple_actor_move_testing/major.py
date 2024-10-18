class Major:

    def __init__(self):
        self.adaptor = None
        self.major_timeout = 60
        self.junior_count = 3
        self.junior_period = 1
        self.gen_count = 3
        self.gen_period = 2
        self.gen_limit = 10
        self.does_gen_ask = False
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
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'major_timeout':
                self.major_timeout = value
            elif name == 'junior_count':
                self.junior_count = value - 1
            elif name == 'junior_period':
                self.junior_period = value
            elif name == 'gen_count':
                self.gen_count = value
            elif name == 'gen_period':
                self.gen_period = value
            elif name == 'gen_limit':
                self.gen_limit = value
            elif name == 'does_gen_ask':
                self.does_gen_ask = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        query = self.adaptor.get_msg('create_process')
        nodes = [(await self.adaptor.ask(query, 4)).get('body').get('node') for _ in range(self.junior_count)]
        nodes.insert(0, self.adaptor.get_node())
        self.junior_count += 1
        names = [f'junior_{index}' for index, _ in enumerate(nodes)]
        class_desc = {'package_name': 'simple_actor_move_testing', 'class': 'Junior'}
        await self.adaptor.group_ask(
            10, len(names), lambda index: {'command': 'create_actor',
                                           'body': {'class_desc': class_desc, 'name': names[index]},
                                           'recipient': nodes[index]})
        body = {'params': [
            {'name': 'parent', 'value': self.adaptor.name},
            {'name': 'junior_period', 'value': self.junior_period},
            {'name': 'gen_count', 'value': self.gen_count},
            {'name': 'gen_period', 'value': self.gen_period},
            {'name': 'gen_limit', 'value': self.gen_limit},
            {'name': 'does_gen_ask', 'value': self.does_gen_ask},
            {'name': 'nodes', 'value': nodes}
        ]}
        await self.adaptor.group_ask(
            10, len(names), lambda index: {'command': 'set_params', 'body': body, 'recipient': names[index]})
        for name in names:
            await self.adaptor.send(self.adaptor.get_msg('start', None, name))
        self.adaptor.start_timer(self.major_timeout)

    async def timer(self):
        await self.adaptor.send(self.adaptor.get_msg('exit', None, self.adaptor.get_head_addr()))

    async def extra_beat(self):
        self.beat_count += 1
        if self.beat_count == self.junior_count:
            await self.adaptor.send(self.adaptor.get_msg('exit', None, self.adaptor.get_head_addr()))
