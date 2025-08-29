
class CircleStarter:

    def __init__(self):
        self.adaptor = None
        self.process_count = None
        self.dancers_per_process = None
        self.period = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'begin':
            await self.begin(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))

    async def begin(self, recipient):
        processes = []
        for _ in range(self.process_count - 1):
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'))
            processes.append(ans.get('body').get('node'))
        processes.insert(0, self.adaptor.get_node())
        await self.adaptor.group_ask(10, len(processes), self.dancers_create_factory(processes))
        names = [f'dancer_{(index * self.dancers_per_process + i):02d}'
                 for index in range(len(processes)) for i in range(self.dancers_per_process)]
        await self.adaptor.group_ask(10, len(names), self.dancers_set_params_factory(names))
        await self.adaptor.send(self.adaptor.get_msg('tick', None, 'dancer_00'))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('begun', None, recipient))

    def dancers_create_factory(self, processes):
        def get_values(index):
            names = [f'dancer_{(index * self.dancers_per_process + i):02d}' for i in range(self.dancers_per_process)]
            body = {'class_desc': {'requires_dist': 'peacepie_example', 'class': 'CircleDancer'}, 'names': names}
            return {'command': 'create_actors', 'body': body, 'recipient': processes[index]}
        return get_values

    def dancers_set_params_factory(self, names):
        def get_values(index):
            body = {
                'params': [
                    {'name': 'consumer', 'value': f'dancer_{index + 1:02d}' if index < len(names) - 1 else 'dancer_00'},
                    {'name': 'period', 'value': self.period}
                ]
            }
            return {'command': 'set_params', 'body': body, 'recipient': names[index]}
        return get_values
