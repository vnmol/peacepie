import asyncio


class CircleDancer:

    def __init__(self):
        self.adaptor = None
        self.consumer = None
        self.period = 1

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'tick':
            await self.tick(msg)
        elif command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'is_ready_to_move':
            await self.is_ready_to_move(sender)
        elif command == 'move':
            await self.move(body, sender)
        else:
            return False
        return True

    async def tick(self, msg):
        print(self.adaptor.get_alias())
        msg['recipient'] = self.consumer
        await asyncio.sleep(self.period)
        await self.adaptor.send(msg)

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'consumer':
                self.consumer = value
            elif name == 'period':
                self.period = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def is_ready_to_move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('ready', None, recipient))

    async def move(self, clone_addr, recipient):
        params = [{'name': 'consumer', 'value': self.consumer}, {'name': 'period', 'value': self.period}]
        await self.adaptor.ask(self.adaptor.get_msg('set_params', {'params': params}, clone_addr))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('moved', None, recipient))
