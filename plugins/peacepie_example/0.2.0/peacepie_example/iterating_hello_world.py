class IteratingHelloWorld:

    def __init__(self):
        self.adaptor = None
        self.period = 1
        self.limit = None
        self.index = 0
        self.is_ticking = False
        self._ticker_name = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        elif command == 'tick_start':
            await self.tick_start(sender)
        elif command == 'tick_stop':
            await self.tick_stop(sender)
        elif command == 'tick':
            await self.tick()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))

    async def start(self, recipient):
        if self.is_ticking:
            self._ticker_name = self.adaptor.add_ticker(self.period)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))

    async def tick_start(self, recipient):
        if self.is_ticking:
            if recipient:
                await self.adaptor.send(self.adaptor.get_msg('tick_already_started', recipient=recipient))
            return
        self.is_ticking = True
        self._ticker_name = self.adaptor.add_ticker(self.period)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('tick_started', recipient=recipient))

    async def tick_stop(self, recipient):
        if not self.is_ticking:
            if recipient:
                await self.adaptor.send(self.adaptor.get_msg('tick_already_stopped', recipient=recipient))
            return
        self.adaptor.remove_ticker(self._ticker_name)
        self._ticker_name = None
        self.index = 0
        self.is_ticking = False
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('tick_stopped', recipient=recipient))

    async def tick(self):
        print(f'{self.adaptor.get_alias()} from "{self.adaptor.get_node()}" says "Hello, World! ({self.index})"')
        self.index += 1
        if self.index == self.limit:
            self.adaptor.remove_ticker(self._ticker_name)
