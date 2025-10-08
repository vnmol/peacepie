import asyncio


class CircleDancer:

    def __init__(self):
        self.adaptor = None
        self.consumer = None
        self.period = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'tick':
            await self.tick(msg)
        elif command == 'set_params':
            await self.set_params(body.get('params'), sender)
        else:
            return False
        return True

    async def tick(self, msg):
        print(f'{self.adaptor.get_alias()} from "{self.adaptor.get_node()}"')
        msg['recipient'] = self.consumer
        await asyncio.sleep(self.period)
        await self.adaptor.send(msg)

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))
