import asyncio
import random
import time

COUNT = 0
TIME = time.time()
PERIOD = 10


class SimpleGen:

    def __init__(self):
        self.adaptor = None
        self.period = 1
        self.consumers = []
        self.index = 0

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'tick':
            await self.tick()
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def tick(self):
        global TIME
        global COUNT
        COUNT += 1
        if time.time() - TIME >= PERIOD:
            print(COUNT / PERIOD, self.adaptor.name, self.adaptor.queue.qsize())
            TIME = time.time()
            COUNT = 0
        if not self.consumers:
            return
        await self.adaptor.send(self.adaptor.get_msg('test', None, recipient=self.consumers[self.index]))
        self.index += 1
        if self.index == len(self.consumers):
            self.index = 0

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'consumers':
                for val in value:
                    self.consumers.append(val)
            elif name == 'period':
                self.period = value
                # self.period = value * (1 + 0.5 * random.random())
            elif name == 'detail_log':
                if not value:
                    self.adaptor.not_log_commands.update(['tick', 'test'])
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        # self.adaptor.add_ticker(self.period)
        asyncio.get_event_loop().create_task(self.process())

    async def process(self):
        async for _ in self.tick_gen():
            await self.tick()

    async def tick_gen(self):
        while True:
            yield 0
            await asyncio.sleep(self.period)
