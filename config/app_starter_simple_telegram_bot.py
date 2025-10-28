import random
import re


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
        await self.telegram()

    async def web_face(self):
        name = 'web_face'
        body = {'class_desc': {'requires_dist': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 60)
        body = {'params': [{'name': 'http_port', 'value': 9090}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name))

    async def telegram(self):
        # for i in range(3):
        #     ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'), 2)
        #     recipient = ans.get('body')
        #     process = re.search(r'-(\d+)', recipient.get('node')).group(1)
        #     names = [f'dummy_{process}_{i:02d}' for i in range(random.randint(15, 25))]
        #     class_desc = {'requires_dist': 'simple_telegram_bot', 'class': 'Dummy'}
        #     body = {'class_desc': class_desc, 'names': names}
        #     await self.adaptor.ask(self.adaptor.get_msg('create_actors', body, recipient), 8)
        name = 'telegram'
        class_desc = {'requires_dist': 'simple_telegram_bot', 'class': 'SimpleTelegramActor'}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 60)
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name), 300)
        await self.adaptor.send(self.adaptor.get_msg('remove_actor', {'name': self.adaptor.name}))
