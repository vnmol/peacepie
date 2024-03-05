class RssVmsInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'Postgres11Installer'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'postgres_installer'})
        ans = await self.adaptor.ask(msg, 30)
        msg = self.adaptor.get_msg('postgres_install', recipient=ans.get('body'))
        await self.adaptor.send(msg)
        '''
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'OpenJdkJava8Installer'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'java_installer'})
        ans = await self.adaptor.ask(msg, 30)
        msg = self.adaptor.get_msg('java_install', recipient=ans.get('body'))
        await self.adaptor.ask(msg, 300)
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'Utf8RuLocaleInstaller'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'ru_installer'})
        ans = await self.adaptor.ask(msg, 30)
        msg = self.adaptor.get_msg('ru_install', recipient=ans.get('body'))
        await self.adaptor.send(msg)
        '''
