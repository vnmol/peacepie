class Worker:

    def __init__(self):
        self.adaptor = None
        self.index = None
        self.group_size = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start(msg.get('timeout'), msg.get('sender'))
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'index':
                self.index = value
            elif name == 'group_size':
                self.group_size = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, timeout, recipient):
        names = [f'dummy_{self.index:02d}_{i:02d}' for i in range(self.group_size)]
        await self.adaptor.group_ask(timeout, len(names), self.dummy_create_factory(names))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))

    def dummy_create_factory(self, names):
        class_desc = {'requires_dist': 'dummy_with_dependencies', 'class': 'Dummy'}

        def get_values(index):
            return {'command': 'create_actor', 'body': {'class_desc': class_desc, 'name': names[index]}}

        return get_values
