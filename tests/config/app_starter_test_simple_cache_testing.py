
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
        name = 'cache_tester'
        body = {'class_desc': {'requires_dist': 'simple_cache_testing', 'class': 'CacheTester'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), timeout=30)
        body = {'params': [{'name': 'node_count', 'value': 4}, {'name': 'action_count', 'value': 200}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
