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


