
class Initiator:

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
        body = msg.get('body') if msg.get('body') else {}
        port = body.get('port') if body.get('port') else 9090
        body = {'class_desc': {'requires_dist': 'peacepie_example', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': port}, ans.get('body')))
        recipient = msg.get('sender')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))
