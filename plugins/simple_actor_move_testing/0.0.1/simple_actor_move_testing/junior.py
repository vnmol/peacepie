import logging
import random


class Junior:

    def __init__(self):
        self.adaptor = None
        self.parent = None
        self.junior_period = 1
        self.gen_count = 3
        self.gen_period = 2
        self.gen_limit = 10
        self.does_gen_ask = False
        self.performers = None
        self.nodes = None
        self.locations = {}
        self.performer_index = 0
        self.ticker = None

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
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'parent':
                self.parent = value
            elif name == 'junior_period':
                self.junior_period = value
            elif name == 'gen_count':
                self.gen_count = value
            elif name == 'gen_period':
                self.gen_period = value
            elif name == 'gen_limit':
                self.gen_limit = value
            elif name == 'does_gen_ask':
                self.does_gen_ask = value
            elif name == 'nodes':
                self.nodes = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        parent_index = int(self.adaptor.name.split('_')[1])
        consumer = f'consumer_{parent_index}'
        body = {'class_desc': {'requires_dist': 'simple_actor_move_testing', 'class': 'Consumer'}, 'name': consumer}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        names = [f'gen_{parent_index}_{i}' for i in range(self.gen_count)]
        body = {'params': [
            {'name': 'parent', 'value': self.parent},
            {'name': 'limits', 'value': {name: self.gen_limit for name in names}}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, consumer))
        await self.adaptor.send(self.adaptor.get_msg('not_log_commands_set', {'commands': ['beat']}, consumer))
        self.performers = list(names)
        self.performers.append(consumer)
        node_index = self.nodes.index(self.adaptor.get_node())
        for performer_index in range(len(self.performers)):
            self.locations[performer_index] = node_index
        class_desc = {'requires_dist': 'simple_actor_move_testing', 'class': 'Generator'}
        await self.adaptor.group_ask(
            10, len(names), lambda index: {'command': 'create_actor',
                                           'body': {'class_desc': class_desc, 'name': names[index]},
                                           'recipient': None})
        body = {'params': [
            {'name': 'gen_period', 'value': self.gen_period},
            {'name': 'gen_limit', 'value': self.gen_limit},
            {'name': 'does_gen_ask', 'value': self.does_gen_ask},
            {'name': 'consumer', 'value': consumer}
        ]}
        await self.adaptor.group_ask(
            10, len(names), lambda index: {'command': 'set_params', 'body': body, 'recipient': names[index]})
        for name in names:
            await self.adaptor.send(self.adaptor.get_msg('not_log_commands_set', {'commands': ['tick', 'beat']}, name))
        for name in names:
            await self.adaptor.send(self.adaptor.get_msg('start', None, name))
        if parent_index == 1:
            self.ticker = self.adaptor.add_ticker(self.junior_period, self.junior_period)

    async def tick(self):
        size = len(self.nodes)
        if size == 1:
            logging.warning('The number of nodes must be more than 1')
            return
        performer = self.performers[self.performer_index]
        old_node = self.nodes[self.locations[self.performer_index]]
        new_node = old_node
        while old_node == new_node:
            new_node = self.nodes[random.randrange(size)]
        ans = await self.adaptor.ask(
            self.adaptor.get_msg('move_actor', {'node': new_node, 'entity': performer}, old_node), 10)
        if ans.get('command') == 'actor_is_moved':
            self.locations[self.performer_index] = self.nodes.index(new_node)
        self.increment()

    def increment(self):
        self.performer_index += 1
        if self.performer_index == len(self.performers):
            self.performer_index = 0
