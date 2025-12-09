class SimpleSqliteDb:

    def __init__(self):
        self.adaptor = None

    async def pre_run(self):
        pass

    async def exit(self):
        pass

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))
