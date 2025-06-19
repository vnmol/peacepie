import time


class Overlooker:

    def __init__(self):
        self.adaptor = None
        self.main_overlooker = None
        self.overlooker_period = None
        self.first = True
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
            self.adaptor.add_ticker(self.overlooker_period, self.overlooker_period)
        body = msg.get('body')
        navi = body.get('navi')
        nd_id = navi.get('id')
        if self.packets.get(nd_id):
            del self.packets[nd_id]
            self.received += 1
        else:
            self.packets[nd_id] = navi

    async def tick(self):
        if self.main_overlooker:
            msg = self.adaptor.get_msg('packets_received', {'received': self.received}, self.main_overlooker)
            await self.adaptor.send(msg)
            self.received = 0

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'main_overlooker':
                self.main_overlooker = value
            elif name == 'overlooker_period':
                self.overlooker_period = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))
