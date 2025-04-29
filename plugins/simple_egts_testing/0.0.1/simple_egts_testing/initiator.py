class Initiator:

    def __init__(self):
        self.adaptor = None
        self.url = None
        self.convertor_desc = None
        self.inet_addr = None
        self.is_embedded_channel = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'extra-index-url':
                self.url = value
            elif name == 'convertor_desc':
                self.convertor_desc = value
            elif name == 'inet_addr':
                self.inet_addr = value
            elif name == 'is_embedded_channel':
                self.is_embedded_channel = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        name = f'tcp_server'
        class_desc = {'package_name': 'simple_networking', 'class': 'TcpServer', 'extra-index-url': self.url}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 30)
        body = {'params': [{'name': 'convertor_desc', 'value': self.convertor_desc},
                           {'name': 'host', 'value': self.inet_addr.get('host')},
                           {'name': 'port', 'value': self.inet_addr.get('port')},
                           {'name': 'is_embedded_channel', 'value': self.is_embedded_channel},
                           {'name': 'consumer', 'value': self.adaptor.name}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name), 4)
        '''
        body = {'commands': ['navi_data', 'received_from_channel', 'send_to_channel', 'sent']}
        await self.adaptor.ask(self.adaptor.get_msg('not_log_commands_set', body, name), 4)
        '''
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name), 30)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))
