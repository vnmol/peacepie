
class Mediator:

    def __init__(self):
        self.adaptor = None
        self.parent = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'send_to_channel':
            await self.send_to_channel(body)
        elif command == 'channel_is_opened':
            await self.channel_operation(msg)
        elif command == 'channel_is_not_opened':
            await self.channel_operation(msg)
        elif command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'error':
            self.error()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            if param.get('name') == 'parent':
                self.parent = param.get('value')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def send_to_channel(self, data):
        self.parent.writer.write(data)
        await self.parent.writer.drain()

    async def channel_operation(self, msg):
        if self.parent.start_queue:
            await self.parent.start_queue.put(msg)

    def error(self):
        self.parent.writer.close()
