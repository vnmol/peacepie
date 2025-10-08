
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
        await self.fastapi()

    async def web_face(self):
        name = 'web_face'
        body = {'class_desc': {'requires_dist': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        body = {'params': [{'name': 'http_port', 'value': 9090}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name))

    async def fastapi(self):
        name = 'fastapi'
        class_desc = {'requires_dist': 'simple_fastapi_dashboard', 'class': 'SimpleFastapiActor'}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        body = {'params': [{'name': 'port', 'value': 8000}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name), 300)
        await self.adaptor.send(self.adaptor.get_msg('remove_actor', {'name': self.adaptor.name}))
