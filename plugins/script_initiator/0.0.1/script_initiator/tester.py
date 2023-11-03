

class ScriptTester:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg['command'] == 'start':
            await self.start()
        else:
            return False
        return True
    
    async def start(self):
        version = {'=': {'major': 0, 'minor': 0, 'micro': 1}}
        class_desc = {'package_name': 'test_tcp_clients', 'version': version, 'class': 'TcpClients'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'tcp_clients'})
        ans = await self.adaptor.ask(msg, 2)
        if ans['command'] != 'actor_is_created':
            return
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=ans['body']))
