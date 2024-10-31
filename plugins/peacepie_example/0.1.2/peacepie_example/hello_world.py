class HelloWorld:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        sender = msg.get('sender')
        if command == 'tick':
            await self.tick(sender)
        elif command == 'is_ready_to_move':
            await self.is_ready_to_move(sender)
        elif command == 'move':
            await self.move(sender)
        return True

    async def tick(self, recipient):
        print('Hello, World!')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('hello_world', None, recipient))

    async def is_ready_to_move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('ready', None, recipient))

    async def move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('moved', None, recipient))
