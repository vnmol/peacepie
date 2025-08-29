import random


class Junior:

    def __init__(self):
        self.adaptor = None
        self.major = None
        self.index = None
        self.junior_count = None
        self.junior_period = None
        self.junior_flags = None
        self.gen_count = None
        self.gen_period = None
        self.gen_limit = None
        self.does_gen_ask = False
        self.skip_some_logging = False
        self.nodes = None
        self.consumer = None
        self.generators = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start()
        elif command == 'tick':
            await self.tick()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        self.nodes.remove(self.adaptor.get_node())
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        msg = self.adaptor.get_msg('not_log_commands_set', {'commands': ['tick', 'beat', 'beaten']})
        await self.adaptor.send(msg)
        self.consumer = f'consumer_{self.index}'
        class_desc = {'requires_dist': 'simple_actor_recreate_testing', 'class': 'Consumer'}
        body = {'class_desc': class_desc, 'name': self.consumer}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        self.generators = [f'gen_{self.index}_{i}' for i in range(self.gen_count)]
        body = {'params': [
            {'name': 'major', 'value': self.major},
            {'name': 'limits', 'value': {generator: self.gen_limit for generator in self.generators}}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, self.consumer))
        if self.skip_some_logging:
            msg = self.adaptor.get_msg('not_log_commands_set', {'commands': ['beat', 'beaten']}, self.consumer)
            await self.adaptor.send(msg)
        class_desc = {'requires_dist': 'simple_actor_recreate_testing', 'class': 'Generator'}
        await self.adaptor.group_ask(
            10, len(self.generators), lambda index: {'command': 'create_actor',
                                           'body': {'class_desc': class_desc, 'name': self.generators[index]},
                                           'recipient': None})
        body = {'params': [
            {'name': 'gen_period', 'value': self.gen_period},
            {'name': 'gen_limit', 'value': self.gen_limit},
            {'name': 'does_gen_ask', 'value': self.does_gen_ask},
            {'name': 'consumer', 'value': self.consumer}
        ]}
        get_values = lambda index: {'command': 'set_params', 'body': body, 'recipient': self.generators[index]}
        await self.adaptor.group_ask(10, len(self.generators), get_values)
        if self.skip_some_logging:
            for generator in self.generators:
                msg = self.adaptor.get_msg('not_log_commands_set', {'commands': ['tick', 'beat', 'beaten']}, generator)
                await self.adaptor.send(msg)
        for generator in self.generators:
            await self.adaptor.send(self.adaptor.get_msg('start', None, generator))
        delay = self.junior_period * (1 + self.index / self.junior_count)
        self.adaptor.add_ticker(self.junior_period, delay)

    async def tick(self):
        entity = random.choice(self.generators)
        if self.junior_flags.get('is_consumer'):
            if self.junior_flags.get('are_generators'):
                if self.junior_flags.get('is_shared_heap'):
                    entity = random.choice(self.generators + [self.consumer])
                elif random.choice([True, False]):
                    entity = self.consumer
            else:
                entity = self.consumer
        ans = await self.adaptor.ask(self.adaptor.get_msg('seek_actor', {'entity': entity}))
        if ans.get('command') != 'actor_found':
            return
        node = ans.get('body').get('node')
        is_moving = False
        if self.junior_flags.get('is_remote'):
            if self.junior_flags.get('is_local'):
                is_moving = random.choice([True, False])
            else:
                is_moving = True
        if is_moving:
            node = random.choice(self.nodes)
        msg = self.adaptor.get_msg('recreate_actor', {'node': node, 'entity': entity})
        await self.adaptor.ask(msg, 8)
