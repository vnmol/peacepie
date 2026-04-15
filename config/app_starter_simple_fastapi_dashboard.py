
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
        await self.simple_fastapi_dashboard()
        await self.adaptor.send(self.adaptor.get_msg('remove_actor', {'name': self.adaptor.name}))

    async def simple_fastapi_dashboard(self):
        name = 'fastapi'
        class_desc = {'requires_dist': 'simple_fastapi_dashboard', 'class': 'SimpleFastapiActor'}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 300)
        body = {'params': [{'name': 'port', 'value': 9090}, {'name': 'page_size', 'value': 5}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name), 15)

