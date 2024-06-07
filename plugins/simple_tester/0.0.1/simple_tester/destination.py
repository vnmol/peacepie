import time

COUNT = 0
TIME = time.time()
PERIOD = 10


class SimpleDest:

    def __init__(self):
        self.adaptor = None

    async def pre_run(self):
        self.adaptor.not_log_commands.update(['test'])

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'test':
            await self.test()
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
