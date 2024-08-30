
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

    async def web_face(self):
        name = 'initiator'
        body = {'class_desc': {'package_name': 'peacepie_example', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 120)
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name))
