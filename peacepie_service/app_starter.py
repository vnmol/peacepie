import logging
import os


class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        logging.info(f'is_root={os.geteuid() == 0}')
        await self.constant_start()
        await self.variable_start(msg)

    async def constant_start(self):
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 60)
        await self.adaptor.send(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))

    async def variable_start(self, msg):
        await self.vms_installer(msg)

    async def vms_installer(self, msg):
        internal_starter = None
        body = msg.get('body')
        if body:
            internal_starter = body.get('internal_starter')
        if not internal_starter:
            internal_starter = 'internal_starter'
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'RssVmsInstaller'}
        body = {'class_desc': class_desc, 'name': 'vms_installer'}
        query = self.adaptor.get_msg('create_actor', body)
        ans = await self.adaptor.ask(query, 60)
        body = {'internal_starter': internal_starter,'stage': 0, 'substage': 0}
        await self.adaptor.send(self.adaptor.get_msg('start', body, recipient=ans.get('body')))
