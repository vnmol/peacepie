class Consumer:

    def __init__(self):
        self.adaptor = None
        self.major = None
        self.limits = {}

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'beat':
            await self.beat(body, sender, msg)
        elif command == 'start':
            pass
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def beat(self, body, recipient, msg):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('beaten', None, recipient))
        gen = body.get('gen')
        limit = body.get('limit')
        if self.limits.get(gen) - limit != 1:
            head = self.adaptor.get_head_addr()
            await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}, head))
            await self.adaptor.send(self.adaptor.get_msg('quit', None, head))
        self.limits[gen] = limit
        if all(value == 0 for value in self.limits.values()):
            await self.adaptor.send(self.adaptor.get_msg('extra_beat', {'source': self.adaptor.name}, self.major))
