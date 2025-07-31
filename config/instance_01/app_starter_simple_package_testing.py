
class AppStarter:

    def __init__(self):
        self.adaptor = None
        self.tcp_server = None
        self.tcp_client = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        # await self.web_face()
        await self.packaging()

    async def web_face(self):
        class_desc = {'requires_dist': 'simple_web_face >0.0.0, <1.0.0, !=0.2.0', 'class': 'SimpleWebFace'}
        body = {'class_desc': class_desc, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 60)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))

    async def packaging(self):
        name = 'initiator'
        class_desc = {'requires_dist': 'simple_package_testing<1.0.0', 'class': 'Initiator'}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 30)
        body = {'params': [
            {'name': 'group_count', 'value': 1},
            {'name': 'group_size', 'value': 1},
            {'name': 'timeout', 'value': 1200}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
