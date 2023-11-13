import asyncio

PERIOD = 10
DO_PRINTING = False


class Initiator:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            name = 'greeter'
            class_desc = {'package_name': 'peacepie_example', 'class': msg['body']['class']}
            body = {'class_desc': class_desc, 'name': name}
            msg = self.adaptor.get_msg('create_actor', body)
            await self.adaptor.ask(msg)
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=name))
        else:
            return False
        return True


class HelloWorld:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        print('Hello, World!')
        return True


class IteratingHelloWorld:

    def __init__(self):
        self.adaptor = None
        self.index = 0

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            self.adaptor.add_ticker(2)
        elif command == 'tick':
            print(f'Hello, World! ({self.index})')
            self.index += 1
        else:
            return False
        return True


class Starter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg['command'] == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        global PERIOD
        global DO_PRINTING
        group_size = msg['body']['group_size']
        group_count = msg['body']['group_count']
        PERIOD = msg['body']['period']
        DO_PRINTING = msg['body']['do_printing']
        class_desc = {'package_name': 'peacepie_example', 'class': 'Tester'}
        names = [[f'tester_{g:02d}_{m:02d}' for m in range(group_size)] for g in range(group_count)]
        flat_names = [member for group in names for member in group]
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': flat_names})
        await self.adaptor.ask(msg, 5)
        coros = [self.init_group(group) for group in names]
        await asyncio.gather(*coros)
        length = len(names)
        for i in range(length):
            await self.adaptor.send(self.adaptor.get_msg('tick', {'stage': 0}, names[i][0]))
            await asyncio.sleep(PERIOD / length)

    async def init_group(self, names):
        await self.set_consumer(names[len(names) - 1], names[0])
        for i in range(len(names) - 1):
            await self.set_consumer(names[i], names[i+1])

    async def set_consumer(self, recipient, value):
        msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'consumer', 'value': value}]}, recipient)
        await self.adaptor.ask(msg)


class Tester:

    def __init__(self):
        self.adaptor = None
        self.consumer = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'tick':
            await self.tick(msg)
        elif command == 'set_params':
            await self.set_params(msg)
        else:
            return False
        return True

    async def tick(self, msg):
        if DO_PRINTING:
            print(self.adaptor.name, msg['body']['stage'])
        msg['body']['stage'] += 1
        msg['recipient'] = self.consumer
        await asyncio.sleep(PERIOD)
        await self.adaptor.send(msg)

    async def set_params(self, msg):
        for param in msg['body']['params']:
            if param['name'] == 'consumer':
                self.consumer = param['value']
        await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=msg['sender']))


