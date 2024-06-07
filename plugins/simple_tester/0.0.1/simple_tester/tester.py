import time

COUNT = 0
TIME = time.time()
PERIOD = 10


class SimpleTester:

    def __init__(self):
        self.adaptor = None
        self.next = None
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
        global TIME
        global COUNT
        COUNT += 1
        if time.time() - TIME >= PERIOD:
            print(COUNT / PERIOD, self.adaptor.name, self.adaptor.queue.qsize())
            TIME = time.time()
            COUNT = 0
        msg = self.adaptor.get_msg('test', None)
        if self.next:
            msg['recipient'] = self.next
            await self.adaptor.send(msg)
        if self.consumer:
            msg['recipient'] = self.consumer
            await self.adaptor.send(msg)

    async def set_params(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        params = body.get('params')
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'next':
                self.next = value
            elif name == 'consumer':
                self.consumer = value
            elif name == 'detail_log':
                if not value:
                    self.adaptor.not_log_commands.add('test')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))
