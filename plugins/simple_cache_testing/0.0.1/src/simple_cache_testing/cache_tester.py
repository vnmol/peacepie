import logging
import random
import sys


class CacheTester:

    def __init__(self):
        self.adaptor = None
        self.node_count = None
        self.action_count = None
        self.inspectors = None


    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        elif command == 'run':
            await self.run()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        await self.adaptor.send(self.adaptor.get_msg('run', None, self.adaptor.name))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))

    async def run(self):
        for _ in range(self.node_count):
            await self.adaptor.ask(self.adaptor.get_msg('create_process'), timeout=4)
        nodes = await self.adaptor.get_local_nodes(True)
        self.inspectors = {}
        for index, node in enumerate(nodes):
            inspector = f'inspector_{index}'
            self.inspectors[inspector] = {'targets': set(), 'cache': {}}
            body = {'class_desc': {'requires_dist': 'simple_cache_testing', 'class': 'Inspector'}, 'name': inspector}
            await self.adaptor.ask(self.adaptor.get_msg('create_actor', body, node))
        try:
            for i in range(self.action_count):
                inspector = f'inspector_{random.randrange(self.node_count)}'
                target = f'target_{random.randrange(self.node_count)}'
                operation = random.randrange(3)
                match operation:
                    case 0:
                        await self.is_exist(inspector, target)
                    case 1:
                        await self.create_target(inspector, target)
                    case 2:
                        await self.remove_target(target)
                await self.check_cache()
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}))
        await self.adaptor.send(self.adaptor.get_msg('quit'))

    async def check_cache(self):
        for inspector in self.inspectors:
            ans = await self.adaptor.ask(self.adaptor.get_msg('get_cache', None, inspector))
            if ans.get('body').get(inspector) != self.inspectors.get(inspector).get('cache'):
                if 'unittest' not in sys.modules:
                    print(
                        inspector,
                        f'Remote: {ans.get("body").get(inspector)}',
                        f'Local: {self.inspectors.get(inspector).get("cache")}')
                raise ValueError

    async def is_exist(self, inspector, target):
        await self.adaptor.ask(self.adaptor.get_msg('is_exist', {'target': target}, inspector))
        for current, val in self.inspectors.items():
            if target in val.get('targets'):
                self.inspectors.get(inspector).get('cache')[target] = 'LOCAL' if current == inspector else 'REMOTE'
                return
        self.inspectors.get(inspector).get('cache')[target] = 'NONE'

    async def create_target(self, inspector, target):
        for val in self.inspectors.values():
            if target in val.get('targets'):
                return
        await self.adaptor.ask(self.adaptor.get_msg('create_target', {'target': target}, inspector))
        self.inspectors.get(inspector).get('targets').add(target)
        for current, val in self.inspectors.items():
            if target in val.get('cache'):
                self.inspectors.get(current).get('cache')[target] = 'LOCAL' if current == inspector else 'REMOTE'
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_cache', None, inspector))

    async def remove_target(self, target):
        inspector = None
        for current, val in self.inspectors.items():
            if target in val.get('targets'):
                inspector = current
                val.get('targets').remove(target)
            if target in val.get('cache'):
                self.inspectors.get(current).get('cache')[target] = 'NONE'
        if inspector:
            await self.adaptor.ask(self.adaptor.get_msg('remove_target', {'target': target}, inspector))
