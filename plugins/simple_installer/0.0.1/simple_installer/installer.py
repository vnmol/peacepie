from simple_installer import signalman


class SimpleInstaller:

    def __init__(self):
        self.adaptor = None
        self.alias = None
        self.signalman = None

    async def pre_run(self):
        self.alias = self.adaptor.get_alias(self)
        self.signalman = signalman.Signalman(self)

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'add_server':
            await self.signalman.add_server(msg)
        elif command == 'connect':
            await self.connect(msg)
        elif command == 'disconnect':
            await self.disconnect(msg)
        else:
            return False
        return True

    async def connect(self, msg):
        port = await self.signalman.connect(msg)
        if not port:
            return
        body = {'addr': {'host': self.adaptor.get_param('ip'), 'port': port}}
        request = self.adaptor.get_msg('inter_connect', body, self.adaptor.get_head_addr())
        await self.adaptor.send(request)

    async def disconnect(self, msg):
        msg = self.adaptor.get_msg('inter_disconnect', msg.get('body'), self.adaptor.get_head_addr())
        await self.adaptor.ask(msg)
        await self.signalman.disconnect(msg)
