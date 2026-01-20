import asyncio


class Inspector:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'get_cache':
            await self.get_cache(sender)
        elif command == 'is_exist':
            await self.is_exist(body, sender)
        elif command == 'create_target':
            await self.create_target(body, sender)
        elif command == 'remove_target':
            await self.remove_target(body, sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))


    async def get_cache(self, recipient):
        if recipient is None:
            return
        res = {}
        for key, val in self.adaptor.parent.cache.items():
            if val is None:
                val = 'NONE'
            elif isinstance(val, asyncio.Queue):
                val = 'LOCAL'
            else:
                val = 'REMOTE'
            res[key] = val
        await self.adaptor.send(self.adaptor.get_msg('cache', {self.adaptor.name: res}, recipient))

    async def is_exist(self, body, recipient):
        if recipient is None:
            return
        res = await self.adaptor.is_exist(body.get('target'))
        await self.adaptor.send(self.adaptor.get_msg('exists',{'result': res}, recipient))

    async def create_target(self, body, recipient):
        body = {'class_desc': {'requires_dist': 'simple_cache_testing', 'class': 'Target'}, 'name': body.get('target')}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        ans['recipient'] = recipient
        await self.adaptor.send(ans)

    async def remove_target(self, body, recipient):
        ans = await self.adaptor.ask(self.adaptor.get_msg('remove_actor', {'name': body.get('target')}))
        ans['recipient'] = recipient
        await self.adaptor.send(ans)
