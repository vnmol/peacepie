import traceback


class Retransmitter:

    def __init__(self):
        super().__init__()
        self.adaptor = None
        self.first = False
        self.consumer = None
        self.mid = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start_test':
            await self.start_test()
        elif command == 'test':
            await self.test(msg)
        elif command == 'set_params':
            await self.set_params(msg)
        else:
            return False
        return True

    async def start_test(self):
        msg = self.adaptor.get_msg('test', recipient=self.consumer)
        self.mid = msg.get('mid')
        await self.adaptor.send(msg)

    async def test(self, msg):
        if self.first:
            await self.adaptor.send(self.adaptor.get_msg('exit', None, self.adaptor.get_head_addr()))
        else:
            msg['recipient'] = self.consumer
            await self.adaptor.send(msg)

    async def set_params(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        recipient = msg.get('sender')
        for param in body.get('params'):
            name = param.get('name')
            value = param.get('value')
            if name == 'consumer':
                self.consumer = value
            elif name == 'first':
                self.first = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))
