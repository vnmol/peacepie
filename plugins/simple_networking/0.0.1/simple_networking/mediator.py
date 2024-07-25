
class Mediator:

    def __init__(self):
        self.adaptor = None
        self.writer = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'send_to_channel':
            await self.send_to_channel(body)
        elif command == 'set_params':
            self.set_params(body.get('params'))
        else:
            return False
        return True

    def set_params(self, params):
        for param in params:
            if param.get('name') == 'writer':
                self.writer = param.get('value')

    async def send_to_channel(self, data):
        self.writer.write(data)
        await self.writer.drain()
