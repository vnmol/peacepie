
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
        body = {'class_desc': {'requires_dist': 'peacepie_example', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 120)
        body = {'params': [{'name': 'http_port', 'value': 9090}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
