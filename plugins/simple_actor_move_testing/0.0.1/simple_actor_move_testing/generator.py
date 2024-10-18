class Generator:

    def __init__(self):
        self.adaptor = None
        self.gen_period = 2
        self.gen_limit = 10
        self.does_gen_ask = False
        self.consumer = None
        self.ticker = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start()
        elif command == 'tick':
            await self.tick()
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
            if name == 'gen_period':
                self.gen_period = value
            elif name == 'gen_limit':
                self.gen_limit = value
            elif name == 'does_gen_ask':
                self.does_gen_ask = value
            elif name == 'consumer':
                self.consumer = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        if self.gen_limit > 0:
            self.ticker = self.adaptor.add_ticker(self.gen_period)

    async def tick(self):
        self.gen_limit -= 1
        body = {'gen': self.adaptor.name, 'limit': self.gen_limit}
        msg = self.adaptor.get_msg('beat', body, self.consumer)
        if self.does_gen_ask:
            msg['sender'] = self.adaptor.name
            await self.adaptor.ask(msg)
        else:
            await self.adaptor.send(msg)
        if self.gen_limit == 0:
            self.adaptor.remove_ticker(self.ticker)

    async def is_ready_to_move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('ready', None, recipient))

    async def move(self, clone_addr, recipient):
        body = {'params': [
            {'name': 'gen_period', 'value': self.gen_period},
            {'name': 'gen_limit', 'value': self.gen_limit},
            {'name': 'does_gen_ask', 'value': self.does_gen_ask},
            {'name': 'consumer', 'value': self.consumer}
        ]}
        msg = self.adaptor.get_control_msg('set_params', body, clone_addr)
        await self.adaptor.ask(msg, 4)
        await self.adaptor.send(self.adaptor.get_control_msg('start', None, clone_addr))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('moved', None, recipient))
