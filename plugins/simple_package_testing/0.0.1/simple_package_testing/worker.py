class Worker:

    def __init__(self):
        self.adaptor = None
        self.index = None
        self.group_size = None
        self.timeout = None

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
            if name == 'index':
                self.index = value
            elif name == 'group_size':
                self.group_size = value
            elif name == 'timeout':
                self.timeout = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        class_desc = {'requires_dist': 'dummy_with_dependencies', 'class': 'Dummy'}
        for i in range(self.group_size):
            name = f'dummy_{self.index:02d}_{i:02d}'
            msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': name}, timeout=self.timeout)
            await self.adaptor.send(msg)
