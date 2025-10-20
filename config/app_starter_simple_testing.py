
class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.web_face()
        await self.tester()

    async def web_face(self):
        name = 'web_face'
        body = {'class_desc': {'requires_dist': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        body = {'params': [{'name': 'http_port', 'value': 9090}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name))

    async def tester(self):
        name = 'initiator'
        body = {'class_desc': {'requires_dist': 'simple_testing', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [{'name': 'group_count', 'value': 10}, {'name': 'group_size', 'value': 10},
                           {'name': 'is_loop', 'value': False},
                           {'name': 'with_dests', 'value': True}, {'name': 'dest_type', 'value': 'for_each'},
                           {'name': 'with_gens', 'value': True}, {'name': 'gen_type', 'value': 'for_each'},
                           {'name': 'period', 'value': 0.001},
                           {'name': 'direct', 'value': False}, {'name': 'detail_log', 'value': False}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
