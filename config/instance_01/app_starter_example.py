
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
        name = 'initiator'
        class_desc = {'package_name': 'peacepie_example', 'class': 'Initiator', 'extra-index-url': 'http://localhost:9000'}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 120)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, name), 10)
