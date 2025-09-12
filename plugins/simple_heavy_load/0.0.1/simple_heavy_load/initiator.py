from datetime import datetime


class Initiator:

    def __init__(self):
        self.adaptor = None
        self.count = 3
        self.does_remove = True
        self.remaining_time = 60

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        print('START', datetime.now().strftime("%H:%M:%S.%f"), self.adaptor.get_caller_info())
        names = []
        nodes = []
        for i in range(self.count):
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'), 10)
            node = ans.get('body').get('node')
            nodes.append(node)
            name = f'burner_{i}'
            names.append(name)
            body = {'class_desc': {'requires_dist': 'simple_heavy_load', 'class': 'Burner'}, 'name': name}
            await self.adaptor.ask(self.adaptor.get_msg('create_actor', body, node), 10)
            body = {'params': [{'name': 'remaining_time', 'value': self.remaining_time}]}
            await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        timeout = self.remaining_time + 20
        await self.adaptor.group_ask(timeout, len(names), lambda index: {'command': 'start', 'recipient': names[index]})
        if self.does_remove:
            for i in range(len(nodes)):
                await self.adaptor.ask(self.adaptor.get_msg('remove_process', {'node': nodes[i]}), 10)
        print('FINISH', datetime.now().strftime("%H:%M:%S.%f"), self.adaptor.get_caller_info())
