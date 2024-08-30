
class Initiator:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        body = {'class_desc': {'package_name': 'peacepie_example', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))
