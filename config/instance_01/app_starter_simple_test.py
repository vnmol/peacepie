
class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.web_face()
        await self.tester()

    async def web_face(self):
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))

    async def tester(self):
        body = {'class_desc': {'package_name': 'simple_tester', 'class': 'Initiator'}, 'name': 'initiator'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'group_count': 3, 'group_size': 10}
        await self.adaptor.send(self.adaptor.get_msg('start', body, ans.get('body')))
