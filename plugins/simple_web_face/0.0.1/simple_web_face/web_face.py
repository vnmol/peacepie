import asyncio
import logging
import multiprocessing

from simple_web_face import http_server

from peacepie import params


class SimpleWebFace:

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
            logging.exception(ex)
        await queue.put(0)

    async def _link_handle(self, reader, writer):
        logging.info(f' Channel ({self.link_host}, {self.link_port}) is opened')
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
                logging.exception(ex)
                reader = None

    async def link_handle(self, msg, serializer, writer):
        command = msg.get('command')
        if command == 'get_members':
            await self.get_members(msg, serializer, writer)
        elif command == 'websocket_handle':
            await self.websocket_handle(msg, serializer, writer)

    async def get_members(self, msg, serializer, writer):
        body = msg.get('body')
        recipient = body.get('recipient')
        if not recipient:
            recipient = self.adaptor.get_head_addr()
        query = self.adaptor.get_msg('get_members', body, recipient)
        ans = await self.adaptor.ask(query)
        await self.send_to_link(ans, serializer, writer)

    async def websocket_handle(self, msg, serializer, writer):
        tp = None
        command = None
        body = None
        recipient = None
        res = None
        try:
            bd = self.adaptor.json_loads(msg.get('body'))
            tp = bd.get('type')
            command = bd.get('command')
            body = bd.get('body')
            recipient = bd.get('recipient')
        except Exception as e:
            logging.exception(e)
            res = {'res': str(e)}
        if res:
            await self.send_to_link(res, serializer, writer)
            return
        query = self.adaptor.get_msg(command, body, recipient)
        if tp == 'ask':
            res = self.adaptor.json_dumps(await self.adaptor.ask(query))
        else:
            await self.adaptor.send(query)
            res = 'The message is sent'
        await self.send_to_link(res, serializer, writer)

    async def send_to_link(self, msg, serializer, writer):
        msg = serializer.__class__.serialize(msg)
        writer.write(msg)
        await writer.drain()

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        http_host = params.instance.get('ip')
        http_port = msg.get('body').get('port') if msg.get('body') else None
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_log_desc'))
        self.process = multiprocessing.Process(
            target=http_server.create,
            args=(ans.get('body'), self.link_host, self.link_port, self.adaptor.get_serializer(), http_host, http_port))
        self.process.start()
