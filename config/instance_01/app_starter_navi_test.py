
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
        name = 'web_face'
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, name))

    async def tester(self):
        name = 'navi_tester'
        body = {'class_desc': {'package_name': 'simple_navi_tester', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'convertor_desc': {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'},
                'count': 1, 'size': 100, 'port': 5000, 'period': 10}
        await self.adaptor.send(self.adaptor.get_msg('start', body, name))
