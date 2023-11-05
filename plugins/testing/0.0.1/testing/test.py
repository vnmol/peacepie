class Starter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg['command'] == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        class_desc = {'package_name': 'testing', 'class': 'Tester'}
        names = [f'tester_{i:02d}' for i in range(5)]
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': names})
        await self.adaptor.ask(msg, 5)


class Tester:

    def __init__(self):
        self.adaptor = None
        self.consumer = None

    async def handle(self, msg):
        command = msg['command']
        if 'command' == 'tick':
            pass
        else:
            return False
        return True
