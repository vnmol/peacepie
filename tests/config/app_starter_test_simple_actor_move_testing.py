
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
        name = 'major'
        body = {'class_desc': {'package_name': 'simple_actor_move_testing', 'class': 'Major'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), timeout=30)
        body = {'params': [
            {'name': 'major_timeout', 'value': 30},
            {'name': 'junior_count', 'value': 4},
            {'name': 'junior_period', 'value': 3},
            {'name': 'gen_count', 'value': 10},
            {'name': 'gen_period', 'value': 0.01},
            {'name': 'gen_limit', 'value': 1000},
            {'name': 'does_gen_ask', 'value': False}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
