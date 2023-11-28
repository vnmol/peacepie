import asyncio
import multiprocessing

from aiohttp import web
from simple_web_face import http_server


class WebFace:

    def __init__(self):
        self.adaptor = None
        self.process = None
        self.link = None
        self.link_host = 'localhost'
        self.link_port = None

    async def pre_run(self):
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.run(queue))
        await queue.get()

    async def run(self, queue):
        try:
            self.link = await asyncio.start_server(self._link_handle, self.link_host, self.link_port)
            self.link_port = self.link.sockets[0].getsockname()[1]
            self.adaptor.logger.info(f'{self.adaptor.get_alias(self)} is started on port {self.link_port}')
        except Exception as ex:
            self.adaptor.logger.exception(ex)
        await queue.put(0)

    async def _link_handle(self, reader, writer):
        self.adaptor.logger.info(f' Channel ({self.link_host}, {self.link_port}) is opened')
        serializer = self.adaptor.get_serializer()
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self.link_handle(res, serializer, writer)
            except Exception as ex:
                self.adaptor.logger.exception(ex)
                reader = None

    async def link_handle(self, msg, serializer, writer):
        command = msg.get('command')
        if command == 'get_processes':
            msg = self.adaptor.get_msg(command, recipient=self.adaptor.get_head_addr())
            ans = await self.adaptor.ask(msg)
            ans_msg = None
            if ans.get('command') == 'processes' and ans.get('body'):
                ans_msg = {'command': 'processes', 'list': ans.get('body').get('list')}
            writer.write(serializer.__class__.serialize(ans_msg))
            await writer.drain()

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        http_port = msg.get('body').get('port') if msg.get('body') else None
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_log_desc'))
        self.process = multiprocessing.Process(
            target=http_server.create,
            args=(ans.get('body'), http_port, self.link_host, self.link_port, self.adaptor.get_serializer()))
        self.process.start()
