class Consumer:

    def __init__(self):
        self.adaptor = None
        self.parent = None
        self.limits = {}

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'beat':
            await self.beat(body)
        elif command == 'is_ready_to_move':
            await self.is_ready_to_move(sender)
        elif command == 'move':
            await self.move(body, sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'parent':
                self.parent = value
            elif name == 'limits':
                self.limits = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def beat(self,body):
        gen = body.get('gen')
        limit = body.get('limit')
        if self.limits.get(gen) - limit != 1:
            head = self.adaptor.get_head_addr()
            await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}, head))
            await self.adaptor.send(self.adaptor.get_msg('exit', None, head))
        self.limits[gen] = limit
        if all(value == 0 for value in self.limits.values()):
            await self.adaptor.send(self.adaptor.get_msg('extra_beat', {'source': self.adaptor.name}, self.parent))

    async def is_ready_to_move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('ready', None, recipient))

    async def move(self, clone_addr, recipient):
        body = {'params': [
            {'name': 'parent', 'value': self.parent},
            {'name': 'limits', 'value': self.limits},
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, clone_addr))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('moved', None, recipient))
