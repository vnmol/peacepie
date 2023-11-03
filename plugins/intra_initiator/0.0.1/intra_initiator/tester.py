import asyncio


class IntraTester:

    def __init__(self):
        self.adaptor = None
        self.consumer = None
        self.kafka_uploader = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'set_params':
            await self.set_params(msg)
        elif command == 'start':
            msg = self.adaptor.get_msg('tick', {'step': 0})
            await self.tick(msg)
        elif command == 'tick':
            await self.tick(msg)
        else:
            return False
        return True

    async def set_params(self, msg):
        for param in msg['body']['params']:
            if param['name'] == 'consumer':
                self.consumer = param['value']
            elif param['name'] == 'kafka_uploader':
                self.kafka_uploader = param['value']
        ans = self.adaptor.get_msg('params_are_set', recipient=msg['sender'])
        await self.adaptor.send(ans)

    async def tick(self, msg):
        await asyncio.sleep(1)
        msg['body']['step'] += 1
        if self.kafka_uploader:
            body = ('0x' + f'{msg["body"]["step"]:04x}'.upper()).encode('utf-8')
            up_msg = self.adaptor.get_msg('bytes', body, self.kafka_uploader)
            await self.adaptor.send(up_msg)
        msg['recipient'] = self.consumer
        await self.adaptor.send(msg)
        print(self.adaptor.name)
