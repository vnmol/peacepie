
class Initiator:

    def __init__(self):
        self.adaptor = None
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
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_process'), 10)
        body = ans.get('body') if ans.get('body') else {}
        node = body.get('node')
        name = 'burner'
        body = {'class_desc': {'requires_dist': 'simple_heavy_load', 'class': 'Burner'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body, node), 10)
        body = {'params':
                    [
                        {'name': 'remaining_time', 'value': self.remaining_time}
                    ]
                }
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name), self.remaining_time + 20)
        await self.adaptor.ask(self.adaptor.get_msg('remove_process', {'node': node}), 10)
