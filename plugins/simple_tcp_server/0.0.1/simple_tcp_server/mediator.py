
class Mediator:

    def __init__(self):
        self.adaptor = None
        self.writer = None

    async def handle(self, msg):
        if msg.command == 'set_params':
            self.set_params(msg.body['params'])
        else:
            return False
        return True

    def set_params(self, params):
        for param in params:
            if param['name'] == 'writer':
                self.writer = param['value']

    async def writing(self, data):
        self.writer.write(data)
        await self.writer.drain()

