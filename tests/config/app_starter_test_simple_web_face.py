
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
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))
        self.adaptor.add_ticker(10, 10, 1)

    async def tick(self):
        head = self.adaptor.get_head_addr()
        await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}, head))
        await self.adaptor.send(self.adaptor.get_msg('exit', None, head))
