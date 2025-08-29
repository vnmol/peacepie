
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
        body = {'class_desc': {'requires_dist': 'simple_actor_recreate_testing', 'class': 'Major'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), timeout=30)
        body = {'params': [
            {'name': 'major_timeout', 'value': 60},
            {'name': 'junior_count', 'value': 4},
            {'name': 'junior_period', 'value': 1},
            {
                'name': 'junior_flags',
                'value':
                    {
                        'is_local': True, 'is_remote': True,
                        'is_consumer': True, 'are_generators': True, 'is_shared_heap': False
                    }
             },
            {'name': 'gen_count', 'value': 10},
            {'name': 'gen_period', 'value': 0.01},
            {'name': 'gen_limit', 'value': 1000},
            {'name': 'does_gen_ask', 'value': True},
            {'name': 'skip_some_logging', 'value': True}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
