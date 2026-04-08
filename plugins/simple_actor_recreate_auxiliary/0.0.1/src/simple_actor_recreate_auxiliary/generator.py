class Generator:

    def __init__(self):
        self.adaptor = None
        self.gen_period = 2
        self.gen_limit = 10
        self.does_gen_ask = False
        self.consumer = None
        self._ticker = None

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
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        if self.gen_limit > 0:
            self._ticker = self.adaptor.add_ticker(self.gen_period)

    async def tick(self):
        self.gen_limit -= 1
        body = {'gen': self.adaptor.name, 'limit': self.gen_limit}
        msg = self.adaptor.get_msg('beat', body, self.consumer)
        if self.does_gen_ask:
            await self.adaptor.ask(msg, 4)
        else:
            await self.adaptor.send(msg)
        if self.gen_limit == 0:
            self.adaptor.remove_ticker(self._ticker)
