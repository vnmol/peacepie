import asyncio
import itertools
import logging

from simple_tcp.channel import Channel
from simple_tcp.embedded_channel import EmbeddedChannel

gen_id = itertools.count()


class SimpleTcpServer:

    def __init__(self):
        self.adaptor = None
        self.port = None
        self.convertor_desc = None
        self.convertor_class = None
        self.embedded_channel = False
        self.consumer = None
        self.server = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'set_params':
            await self.set_params(msg)
        elif command == 'start':
            await self.start(msg.get('sender'))
        else:
            return False
        return True

    async def set_params(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        params = body.get('params')
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'port':
                self.port = value
            elif name == 'convertor_desc':
                self.convertor_desc = value
            elif name == 'embedded_channel':
                self.embedded_channel = value
            elif name == 'consumer':
                self.consumer = value
        await self.embedded()
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def embedded(self):
        if not self.embedded_channel:
            return
        if not self.convertor_desc:
            return
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_class', {'class_desc': self.convertor_desc}))
        if ans.get('command') == 'class':
            self.convertor_class = ans.get('body')

    async def start(self, recipient):
        try:
            self.server = await asyncio.start_server(self.handle_connection, None, self.port)
            logging.info(f'{self.adaptor.get_alias()} is started on port {self.port}')
            if recipient:
                await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))
        except Exception as ex:
            logging.exception(ex)

    async def handle_connection(self, reader, writer):
        channel = None
        try:
            if self.embedded_channel:
                channel = EmbeddedChannel(self, reader, writer)
            else:
                channel = Channel(self, reader, writer)
        except Exception as ex:
            logging.exception(ex)
        if channel:
            await channel.handle()
