
class AppStarter:

    def __init__(self):
        self.adaptor = None
        self.remaining_time =None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.web_face()
        await self.burner()

    async def web_face(self):
        name = 'web_face'
        body = {'class_desc': {'requires_dist': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': name}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        body = {'params': [{'name': 'http_port', 'value': 9090}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, ans.get('body')))

    async def burner(self):
        name = 'initiator'
        body = {'class_desc': {'requires_dist': 'simple_heavy_load', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), timeout=10)
        body = {'params': [
            {'name': 'count', 'value': 3},
            {'name': 'does_remove', 'value': False},
            {'name': 'remaining_time', 'value': 60}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
