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
        await self.constant_start()
        await self.variable_start()

    async def constant_start(self):
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 30)
        await self.adaptor.send(self.adaptor.get_msg('start', {'port': 8080}, ans.get('body')))

    async def variable_start(self):
        pass
        '''
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'RssVmsInstaller'}
        body = {'class_desc': class_desc, 'name': 'vms_installer'}
        query = self.adaptor.get_msg('create_actor', body)
        ans = await self.adaptor.ask(query, 30)
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=ans.get('body')))
        '''
