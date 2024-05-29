import time

COUNT = 0
TIME = time.time()
TIME_COUNT = 0


class SimpleTester:

    def __init__(self):
        self.adaptor = None
        self.consumer = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'test':
            await self.test()
        elif command == 'set_params':
            await self.set_params(msg)
        else:
            return False
        return True

    async def test(self):
        global COUNT
        global TIME_COUNT
        COUNT += 1
        period = time.time() - TIME
        period_count = period // 10
        if period_count > TIME_COUNT:
            TIME_COUNT = period_count
            print(COUNT / period)
        msg = self.adaptor.get_msg('test', None, self.consumer)
        await self.adaptor.send(msg)

    async def set_params(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        params = body.get('params')
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'consumer':
                self.consumer = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))
