import asyncio
import random


class Initiator:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'start':
            await self.start(body)
        else:
            return False
        return True

    async def start(self, body):
        group_count = body.get('group_count')
        group_size = body.get('group_size')
        groups = [[f'tester_{m:02d}_{n:02d}' for n in range(group_size)] for m in range(group_count)]
        names = [item for sublist in groups for item in sublist]
        body = {'class_desc': {'package_name': 'simple_tester', 'class': 'SimpleTester'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 3)
        await self.adaptor.group_ask(10, len(names), cumulative_factory(names))
        for group in groups:
            await self.adaptor.group_ask(10, len(group), consumer_factory(group))
        for group in groups:
            await asyncio.sleep(random.uniform(0.01, 0.1))
            await self.adaptor.send(self.adaptor.get_msg('test', None, group[0]))


def cumulative_factory(names):

    def get_values(index):
        body = {'command': 'test'}
        return {'command': 'cumulative_command_set', 'body': body, 'recipient': names[index]}

    return get_values


def consumer_factory(names):
    size = len(names)

    def get_values(index):
        body = {'params': [{'name': 'consumer', 'value': names[(index + 1) % size]}]}
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values
