class Dummy:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        sender = msg.get('sender')
        if command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def start(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))
