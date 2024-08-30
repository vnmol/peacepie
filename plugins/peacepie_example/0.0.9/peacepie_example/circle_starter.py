import asyncio


class CircleStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg['command'] == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        process_count = msg['body']['process_count']
        period = msg['body']['period']
        processes = []
        for _ in range(process_count - 1):
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'))
            processes.append(ans['body']['node'])
        processes.insert(0, self.adaptor.get_node())
        coroutines = [self.init_process(index, process, period) for index, process in enumerate(processes)]
        await asyncio.gather(*coroutines)
        first = 'dancer_00'
        params = [{'name': 'consumer', 'value': first}]
        recipient = f'dancer_{(len(processes) * 2 - 1):02d}'
        await self.adaptor.ask(self.adaptor.get_msg('set_params', {'params': params}, recipient))
        await self.adaptor.send(self.adaptor.get_msg('tick', None, first))
        if msg.get('sender'):
            await self.adaptor.send(self.adaptor.get_msg('started', None, msg.get('sender')))

    async def init_process(self, index, process, period):
        class_desc = {'package_name': 'peacepie_example', 'class': 'CircleDancer'}
        name0 = f'dancer_{(index * 2):02d}'
        name1 = f'dancer_{(index * 2 + 1):02d}'
        name2 = f'dancer_{(index * 2 + 2):02d}'
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': name0}, process)
        await self.adaptor.ask(msg)
        msg['body']['name'] = name1
        await self.adaptor.ask(msg)
        params = [{'name': 'consumer', 'value': name1}, {'name': 'period', 'value': period}]
        msg = self.adaptor.get_msg('set_params', {'params': params}, name0)
        await self.adaptor.ask(msg)
        params = [{'name': 'consumer', 'value': name2}, {'name': 'period', 'value': period}]
        msg = self.adaptor.get_msg('set_params', {'params': params}, name1)
        await self.adaptor.ask(msg)
