import time


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
        await self.tcp_server_start()
        await self.tcp_client_start()
        await self.remove()

    async def tcp_server_start(self):
        self.tcp_server = 'tcp_server'
        body = {'class_desc': {'package_name': 'simple_networking', 'class': 'TcpServer'}, 'name': self.tcp_server}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [
            {'name': 'convertor_desc', 'value': {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'}},
            {'name': 'host', 'value': '0.0.0.0'}, {'name': 'port', 'value': 5000},
            {'name': 'is_embedded_channel', 'value': True}, {'name': 'consumer', 'value': None},
            {'name': 'is_on_demand', 'value': True}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, self.tcp_server))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, self.tcp_server))

    async def tcp_client_start(self):
        self.tcp_client = 'tcp_client'
        body = {'class_desc': {'package_name': 'simple_networking', 'class': 'TcpClient'}, 'name': self.tcp_client}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        body = {'params': [
            {'name': 'convertor_desc', 'value': {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'}},
            {'name': 'host', 'value': '0.0.0.0'}, {'name': 'port', 'value': 5000},
            {'name': 'is_embedded_channel', 'value': True}, {'name': 'is_on_demand', 'value': True}
        ]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, self.tcp_client))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, self.tcp_client))
        data = {'id': self.adaptor.series_next('navi_id'), 'type': None, 'code': '000000000000001',
                'is_proprietary': False, 'navi': {'time': time.time(), 'lat': 58.0, 'lon': 39.0}}
        await self.adaptor.ask(self.adaptor.get_msg('send_to_channel', data, self.tcp_client))

    async def remove(self):
        await self.adaptor.ask(self.adaptor.get_msg('remove_actor', {'name': self.tcp_server}))

