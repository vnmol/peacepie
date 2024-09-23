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
        if command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start(msg.get('sender'))
        elif command == 'stop':
            await self.stop(msg.get('sender'))
        elif command == 'tick':
            await self.tick()
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
        print(f'{self.adaptor.get_alias()} says "Hello, World! ({self.index})"')
        self.index += 1
        if self.index == self.limit:
            self.adaptor.remove_ticker(self.ticker_name)
