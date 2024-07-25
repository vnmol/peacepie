class Overlooker:

    def __init__(self):
        self.adaptor = None
        self.first = True
        self.is_received = False
        self.limit = 0
        self.period = 1
        self.received = 0
        self.packets = {}

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'navi_data':
            await self.navi_data(msg)
        elif command == 'tick':
            await self.tick()
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        else:
            return False
        return True

    async def navi_data(self, msg):
        if self.first:
            self.first = False
            # self.adaptor.add_ticker(self.period)
        self.is_received = True
        nd = msg.get('body')
        nd_id = nd.get('id')
        if self.packets.get(nd_id):
            del self.packets[nd_id]
            self.received += 1
            if self.received == self.limit:
                await self.adaptor.send(self.adaptor.get_msg('exit', None, self.adaptor.get_head_addr()))
        else:
            self.packets[nd_id] = nd

    async def tick(self):
        if not self.is_received:
            head = self.adaptor.get_head_addr()
            if self.received < self.limit:
                await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()},
                                                             head))
            await self.adaptor.send(self.adaptor.get_msg('exit', None, head))
        self.is_received = False

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'limit':
                self.limit = value
            elif name == 'period':
                self.period = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))
