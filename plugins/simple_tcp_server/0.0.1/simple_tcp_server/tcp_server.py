import asyncio
import itertools

from simple_tcp_server.channel import Channel
from simple_tcp_server.embedded_channel import EmbeddedChannel

gen_id = itertools.count()


class SimpleTcpServer:

    def __init__(self):
        self.adaptor = None
        self.port = None
        self.convertor_desc = None
        self.convertor_class = None
        self.embedded_channel = False
        self.balancer = None
        self.router = None
        self.server = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'set_params':
            await self.set_params(msg['body']['params'])
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def set_params(self, params):
        for param in params:
            if param['name'] == 'port':
                self.port = param['value']
            elif param['name'] == 'convertor_desc':
                self.convertor_desc = param['value']
                await self.embedded()
            elif param['name'] == 'embedded_channel':
                self.embedded_channel = param['value']
                await self.embedded()
            elif param['name'] == 'balancer':
                self.balancer = param['value']
            elif param['name'] == 'router':
                self.router = param['value']

    async def embedded(self):
        if not self.embedded_channel:
            return
        if not self.convertor_desc:
            return
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_class', {'class_desc': self.convertor_desc}))
        if ans['command'] == 'class':
            self.convertor_class = ans['body']

    async def start(self):
        try:
            self.server = await asyncio.start_server(self.handle_connection, None, self.port)
            self.adaptor.logger.info(f'{self.adaptor.get_alias()} is started on port {self.port}')
        except Exception as ex:
            self.adaptor.logger.exception(ex)

    async def handle_connection(self, reader, writer):
        channel = None
        try:
            if self.embedded_channel:
                channel = EmbeddedChannel(self, reader, writer)
            else:
                channel = Channel(self, reader, writer)
        except Exception as ex:
            self.adaptor.logger.exception(ex)
        print(channel.name)
        if channel:
            await channel.handle()
