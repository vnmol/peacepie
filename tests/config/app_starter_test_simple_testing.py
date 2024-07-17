
class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        elif command == 'tick':
            await self.tick()
        else:
            return False
        return True

    async def start(self):
        name = 'initiator'
        body = {'class_desc': {'package_name': 'simple_testing', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [{'name': 'group_count', 'value': 2}, {'name': 'group_size', 'value': 2}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
        self.adaptor.add_ticker(10, 10, 1)

    async def tick(self):
        head = self.adaptor.get_head_addr()
        await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}, head))
        await self.adaptor.send(self.adaptor.get_msg('exit', None, head))
