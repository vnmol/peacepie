
class Initiator:

    def __init__(self):
        self.adaptor = None
        self.group_count = 2
        self.group_size = 2

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'set_params':
            await self.set_params(msg)
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def set_params(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        recipient = msg.get('sender')
        for param in body.get('params'):
            name = param.get('name')
            value = param.get('value')
            if name == 'group_count':
                self.group_count = value
            elif name == 'group_size':
                self.group_size = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        await self.retransmitters()

    async def retransmitters(self):
        all_names = []
        names = [f'retransmitter_main_{j:02d}' for j in range(self.group_size)]
        body = {'class_desc': {'requires_dist': 'simple_testing', 'class': 'Retransmitter'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body))
        all_names.extend(names)
        for i in range(self.group_count-1):
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'), timeout=2)
            names = [f'retransmitter_{i:02d}_{j:02d}' for j in range(self.group_size)]
            body = {'class_desc': {'requires_dist': 'simple_testing', 'class': 'Retransmitter'}, 'names': names}
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_actors', body, ans.get('body')))
            if ans.get('command') == 'actors_are_created':
                all_names.extend(names)
        await self.adaptor.group_ask(10, len(all_names), consumer_factory(all_names))
        await self.adaptor.send(self.adaptor.get_msg('start_test', None, all_names[0]))


def consumer_factory(names):

    def get_values(index):
        value = names[0] if index == len(names)-1 else names[index+1]
        body = {'params': [{'name': 'consumer', 'value': value}]}
        if index == 0:
            body.get('params').append({'name': 'first', 'value': True})
        return {'command': 'set_params', 'body': body, 'recipient': names[index]}

    return get_values

