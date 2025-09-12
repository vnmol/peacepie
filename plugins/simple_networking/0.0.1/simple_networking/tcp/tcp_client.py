import asyncio
import logging

from simple_networking.channel import Channel
from simple_networking.embedded_channel import EmbeddedChannel


class TcpClient:

    def __init__(self):
        self.adaptor = None
        self.must_be_shielded = True
        self.is_client = True
        self.host = None
        self.port = None
        self.convertor_desc = None
        self.convertor_params = {}
        self.is_embedded_channel = False
        self.consumer = None
        self.convertor_class = None
        self.is_on_demand = False
        self.channel = None
        self.channel_queue = None
        self.is_opened = False

    async def exit(self):
        if self.is_opened:
            self.is_opened = False
            if self.channel:
                await self.channel.exit()
        logging.info(f'{self.adaptor.get_alias()} is stopped at {self.host}:{self.port}')

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'send_to_channel':
            await self.send_to_channel(msg)
        elif command == 'set_params':
            await self.set_params(msg)
        elif command == 'start':
            await self.start(msg.get('sender'))
        elif command == 'close':
            await self.close()
        else:
            return False
        return True

    async def send_to_channel(self, msg):
        if not self.is_opened:
            self.channel_queue = asyncio.Queue()
            timeout = msg.get('timeout') if msg.get('timeout') else 4
            self.adaptor.start_timer(timeout, self.channel_queue, msg.get('mid'))
            asyncio.get_running_loop().create_task(self.handle_connection())
            ans = await self.channel_queue.get()
            if ans.get('command') != 'channel_is_opened':
                recipient = msg.get('sender')
                if recipient:
                    ans['recipient'] = recipient
                    await self.adaptor.send(ans)
                return
        await self.channel.send_to_channel(msg)

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
            elif name == 'convertor_params':
                self.convertor_params = value
            elif name == 'is_embedded_channel':
                self.is_embedded_channel = value
            elif name == 'is_on_demand':
                self.is_on_demand = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        if self.is_embedded_channel:
            ans = await self.adaptor.ask(self.adaptor.get_msg('get_class', {'class_desc': self.convertor_desc}))
            self.convertor_class = ans.get('body')
        if not self.is_on_demand:
            self.channel_queue = asyncio.Queue()
            asyncio.get_running_loop().create_task(self.handle_connection())
            ans = await self.channel_queue.get()
            if ans.get('command') != 'channel_is_opened':
                return
        logging.info(f'{self.adaptor.get_alias()} is started at {self.host}:{self.port}')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))

    async def handle_connection(self):
        self.is_opened = True
        is_first = True
        while True:
            try:
                if is_first:
                    is_first = False
                else:
                    await asyncio.sleep(20)
                reader, writer = await asyncio.open_connection(self.host, self.port)
            except Exception as ex:
                logging.exception(ex)
                await asyncio.sleep(10)
                continue
            channel = None
            try:
                if self.is_embedded_channel:
                    channel = EmbeddedChannel(self, reader, writer)
                else:
                    channel = Channel(self, reader, writer)
            except Exception as ex:
                logging.exception(ex)
            if channel:
                self.channel = channel
                channel.not_log_commands = self.adaptor.not_log_commands
                await self.channel.handle(self.channel_queue)
                self.channel = None
            if self.is_on_demand:
                return
            if not self.is_opened:
                return

    async def close(self):
        self.is_opened = False
        if self.channel:
            await self.channel.close()
        self.channel = None
