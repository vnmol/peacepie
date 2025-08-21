class Initiator:

    def __init__(self):
        self.adaptor = None
        self.group_count = None
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
            if name == 'group_count':
                self.group_count = value
            elif name == 'group_size':
                self.group_size = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, timeout, recipient):
        names = [f'worker_{index:02d}' for index in range(self.group_count)]
        await self.adaptor.group_ask(30, len(names), self.worker_create_factory(names))
        await self.adaptor.group_ask(30, len(names), self.worker_set_params_factory(names))
        await self.adaptor.group_ask(timeout, len(names),
                                     lambda index: {'command': 'start', 'recipient': names[index]})
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))

    def worker_create_factory(self, names):
        class_desc = {'requires_dist': 'simple_package_testing', 'class': 'Worker'}

        def get_values(index):
            return {'command': 'create_actor', 'body': {'class_desc': class_desc, 'name': names[index]}}

        return get_values

    def worker_set_params_factory(self, names):

        def get_values(index):
            body = {'params': [
                {'name': 'index', 'value': index},
                {'name': 'group_size', 'value': self.group_size}
            ]}
            return {'command': 'set_params', 'body': body, 'recipient': names[index]}

        return get_values
