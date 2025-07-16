
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
        is_embedded_channel = self.adaptor.get_test_param('is_embedded_channel')
        name = 'initiator'
        body = {'class_desc': {'requires_dist': 'simple_navi_testing', 'class': 'MainInitiator'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        class_desc = {'requires_dist': 'egts_convertor', 'class': 'EGTSConvertor'}
        # class_desc = {'requires_dist': 'simple_convertor', 'class': 'SimpleConvertor'}
        body = {'params': [
            {'name': 'convertor_desc', 'value': class_desc},
            {'name': 'inet_addr', 'value': {'host': '0.0.0.0', 'port': 5000}},
            {'name': 'is_single_channel', 'value': False},
            {'name': 'is_embedded_channel', 'value': is_embedded_channel},
            {'name': 'is_on_demand', 'value': True},
            {'name': 'count', 'value': 3},
            {'name': 'size', 'value': 10},
            {'name': 'period', 'value': 1},
            {'name': 'limit', 'value': 10},
            {'name': 'timeout', 'value': 10},
            {'name': 'overlooker_period', 'value': 4},
            {'name': 'skip_some_logging', 'value': True},
            {'name': 'is_testing', 'value': True}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.send(self.adaptor.get_msg('start', None, name))
