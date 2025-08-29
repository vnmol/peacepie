class HelloWorld:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'tick':
            await self.tick(sender)
        elif command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))

    async def tick(self, recipient):
        print('Hello, World!')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('hello_world', None, recipient))

    async def start(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))
