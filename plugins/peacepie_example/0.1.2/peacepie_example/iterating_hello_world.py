class IteratingHelloWorld:

    def __init__(self):
        self.adaptor = None
        self.period = 1
        self.limit = None
        self.index = 0
        self.ticker_name = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        elif command == 'stop':
            await self.stop(sender)
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
            if name == 'period':
                self.period = value
            elif name == 'limit':
                self.limit = value
            elif name == 'index':
                self.index = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        if self.ticker_name:
            return
        self.ticker_name = self.adaptor.add_ticker(self.period)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))

    async def stop(self, recipient):
        if not self.ticker_name:
            return
        self.adaptor.remove_ticker(self.ticker_name)
        self.ticker_name = None
        self.index = 0
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('stopped', recipient=recipient))

    async def tick(self):
        print(f'{self.adaptor.get_alias()} from "{self.adaptor.get_node()}" says "Hello, World! ({self.index})"')
        self.index += 1
        if self.index == self.limit:
            self.adaptor.remove_ticker(self.ticker_name)

    async def is_ready_to_move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('ready', None, recipient))

    async def move(self, clone_addr, recipient):
        body = {'params': [
            {'name': 'period', 'value': self.period},
            {'name': 'limit', 'value': self.limit},
            {'name': 'index', 'value': self.index}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, clone_addr), 4)
        await self.adaptor.ask(self.adaptor.get_msg('start', None, clone_addr), 4)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('moved', None, recipient))
