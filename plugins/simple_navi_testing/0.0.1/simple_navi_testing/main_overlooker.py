class MainOverlooker:

    def __init__(self):
        self.adaptor = None
        self.limit = None
        self.timeout = None
        self.overlooker_period = None
        self.is_testing = False
        self.first = True
        self.received = 0
        self.received_for_the_period = 0

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'packets_received':
            await self.packets_received(msg)
        elif command == 'tick':
            await self.tick()
        elif command == 'timer':
            await self.timer()
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        else:
            return False
        return True

    async def packets_received(self, msg):
        if self.first:
            self.first = False
            if self.timeout:
                self.adaptor.start_timer(self.timeout)
            self.adaptor.add_ticker(self.overlooker_period, self.overlooker_period)
            if not self.is_testing:
                print('START', self.adaptor.get_caller_info())
        received = msg.get('body').get('received')
        self.received += received
        self.received_for_the_period += received
        if self.received == self.limit:
            await self.adaptor.send(self.adaptor.get_msg('exit', None, self.adaptor.get_head_addr()))

    async def tick(self):
        if not self.is_testing:
            print(self.received_for_the_period / self.overlooker_period, self.adaptor.get_caller_info())
        self.received_for_the_period = 0

    async def timer(self):
        head = self.adaptor.get_head_addr()
        await self.adaptor.send(self.adaptor.get_msg('test_error', {'msg': self.adaptor.get_caller_info()}, head))
        await self.adaptor.send(self.adaptor.get_msg('exit', None, head))

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'limit':
                self.limit = value
            elif name == 'timeout':
                self.timeout = value
            elif name == 'overlooker_period':
                self.overlooker_period = value
            elif name == 'is_testing':
                self.is_testing = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))
