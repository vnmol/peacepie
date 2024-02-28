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
        msg = self.adaptor.get_msg('create_process', None, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(msg)
        if ans.get('command') != 'actor_is_created':
            return
        process_addr = ans.get('body')
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'OpenJdkJava8Installer'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'java_installer'}, process_addr)
        ans = await self.adaptor.ask(msg, 10)
        msg = self.adaptor.get_msg('java_install', recipient=ans.get('body'))
        await self.adaptor.send(msg)
