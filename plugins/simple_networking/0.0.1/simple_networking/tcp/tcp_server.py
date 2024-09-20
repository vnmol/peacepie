import asyncio
import logging

from simple_networking.channel import Channel
from simple_networking.embedded_channel import EmbeddedChannel


class TcpServer:

    def __init__(self):
        self.adaptor = None
        self.host = None
        self.port = None
        self.convertor_desc = None
        self.is_embedded_channel = False
        self.consumer = None
        self.convertor_class = None
        self.channels = []
        self.server = None

    async def exit(self):
        for channel in self.channels:
            await channel.exit()
        self.channels.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logging.info(f'{self.adaptor.get_alias()} is stopped at {self.host}:{self.port}')

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'set_params':
            await self.set_params(msg)
        elif command == 'start':
            await self.start(msg.get('sender'))
        elif command == 'close_all':
            await self.close_all()
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
            if name == 'host':
                self.host = value
            if name == 'port':
                self.port = value
            elif name == 'convertor_desc':
                self.convertor_desc = value
            elif name == 'is_embedded_channel':
                self.is_embedded_channel = value
            elif name == 'consumer':
                self.consumer = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, msg):
        if self.is_embedded_channel:
            ans = await self.adaptor.ask(self.adaptor.get_msg('get_class', {'class_desc': self.convertor_desc}),
                                         msg.get('timeout'))
            self.convertor_class = ans.get('body')
        self.server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        logging.info(f'{self.adaptor.get_alias()} is started at {self.host}:{self.port}')
        if msg.get('sender'):
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=msg.get('sender')))

    async def handle_connection(self, reader, writer):
        channel = None
        try:
            if self.is_embedded_channel:
                channel = EmbeddedChannel(self, reader, writer)
            else:
                channel = Channel(self, reader, writer)
        except Exception as ex:
            logging.exception(ex)
        if channel:
            channel.not_log_commands = self.adaptor.not_log_commands
            self.channels.append(channel)
            await channel.handle(None)
            self.channels.remove(channel)

    async def close_all(self):
        for channel in self.channels:
            await channel.close()
        self.channels.clear()
