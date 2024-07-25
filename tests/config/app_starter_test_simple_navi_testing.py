
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
        name = 'initiator'
        body = {'class_desc': {'package_name': 'simple_navi_testing', 'class': 'Initiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        is_embedded_channel = self.adaptor.get_test_param('is_embedded_channel')
        body = {'params': [
            {'name': 'convertor_desc', 'value': {'package_name': 'simple_convertor', 'class': 'SimpleConvertor'}},
            {'name': 'inet_addr', 'value': {'host': '0.0.0.0', 'port': 5000}},
            {'name': 'is_embedded_channel', 'value': is_embedded_channel},
            {'name': 'count', 'value': 10},
            {'name': 'size', 'value': 10},
            {'name': 'period', 'value': 1},
            {'name': 'limit', 'value': 10}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
