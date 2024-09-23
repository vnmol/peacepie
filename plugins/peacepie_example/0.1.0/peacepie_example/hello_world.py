class HelloWorld:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        print('Hello, World!')
        if msg.get('sender'):
            await self.adaptor.send(self.adaptor.get_msg('hello_world', None, msg.get('sender')))
        return True
