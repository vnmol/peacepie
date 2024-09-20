
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
        url = 'http://localhost:9000'
        await self.web_face(url)
        await self.networking(url)

    async def web_face(self, url):
        class_desc = {'package_name': 'simple_web_face', 'class': 'SimpleWebFace', 'extra-index-url': url}
        body = {'class_desc': class_desc, 'name': 'web_face'}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 30)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, ans.get('body')))

    async def networking(self, url):
        name = 'main_initiator'
        class_desc = {'package_name': 'simple_navi_testing', 'class': 'MainInitiator', 'extra-index-url': url}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 30)
        class_desc = {'package_name': 'simple_convertor', 'class': 'SimpleConvertor', 'extra-index-url': url}
        body = {'params': [
            {'name': 'extra-index-url', 'value': url},
            {'name': 'convertor_desc', 'value': {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'}},
            {'name': 'inet_addr', 'value': {'host': '0.0.0.0', 'port': 5000}},
            {'name': 'is_embedded_channel', 'value': True},
            {'name': 'is_on_demand', 'value': True},
            {'name': 'count', 'value': 1},
            {'name': 'size', 'value': 10},
            {'name': 'period', 'value': 1.0},
            {'name': 'limit', 'value': None},
            {'name': 'timeout', 'value': None},
            {'name': 'overlooker_period', 'value': 4},
            {'name': 'is_testing', 'value': False}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
