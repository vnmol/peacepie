
class AppStarter:

    def __init__(self):
        self.adaptor = None
        self.tcp_server = None
        self.tcp_client = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.web_face()
        await self.networking()

    async def web_face(self):
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))

    async def networking(self):
        name = 'main_initiator'
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'MainInitiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [
            {'name': 'convertor_desc', 'value': {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'}},
            {'name': 'inet_addr', 'value': {'host': '0.0.0.0', 'port': 5000}},
            {'name': 'is_embedded_channel', 'value': True},
            {'name': 'is_on_demand', 'value': True},
            {'name': 'count', 'value': 4},
            {'name': 'size', 'value': 1000},
            {'name': 'period', 'value': 0.4},
            {'name': 'limit', 'value': None},
            {'name': 'timeout', 'value': None},
            {'name': 'overlooker_period', 'value': 4},
            {'name': 'is_testing', 'value': False}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
