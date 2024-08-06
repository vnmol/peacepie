import asyncio
import logging

from peacepie import params, msg_factory
from peacepie.assist import log_util, timer, serialization
from peacepie.control.intra import intra_queue
from peacepie.control.intra.intra_link import IntraLink


class IntraClient(IntraLink):

    def __init__(self, parent):
        super().__init__(parent)
        self.writer = None

    async def run(self, queue):
        await self.start_server()
        asyncio.get_running_loop().create_task(
            self.start_client(params.instance['intra_host'], params.instance['intra_port'], queue, True))

    async def start_server(self):
        try:
            self.server = await asyncio.start_server(self.server_handle, self.host, 0)
            self.port = self.server.sockets[0].getsockname()[1]
            logging.info(f'{log_util.get_alias(self)} is started on port {self.port}')
        except Exception as ex:
            logging.exception(ex)

    async def server_handle(self, reader, writer):
        serializer = serialization.Serializer()
        body = {'name': self.parent.adaptor.name, 'addr': {'host': self.host, 'port': self.port}}
        msg = msg_factory.get_msg('intra_link', body)
        writer.write(serializer.serialize(msg))
        await writer.drain()
        if msg.get('command') not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.sync_sent_log(self, msg))
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self.handle(res, writer, None)
            except Exception as ex:
                logging.exception(ex)
                reader = None

    async def start_client(self, host, port, queue, is_to_head):
        while True:
            try:
                reader, self.writer = await asyncio.open_connection(host, port)
                logging.info(log_util.get_alias(self) + f' Channel to ({host}, {port}) is opened')
                await self.client_handle(reader, self.writer, queue, is_to_head)
            except Exception as ex:
                logging.exception(ex)
            await asyncio.sleep(10)

    async def exit(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.server.close()
        await self.server.wait_closed()
        logging.info(f'IntraClient on port {self.port} is closed')

    async def client_handle(self, reader, writer, queue, is_to_head):
        serializer = serialization.Serializer()
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self.handle(res, writer, queue, is_to_head)
            except Exception as ex:
                logging.exception(ex)
                reader = None
        if self.head:
            logging.info(log_util.get_alias(self) + ' Channel is closed')
            await self.links[self.head].close()
            self.head = None

    async def handle(self, msgs, writer, queue, is_to_head=False):
        for msg in msgs:
            command = msg.get('command')
            if command not in self.parent.adaptor.not_log_commands:
                logging.debug(log_util.sync_received_log(self, msg))
            if command == 'intra_link':
                body = msg.get('body')
                name = None
                addr = None
                if body:
                    name = body.get('name')
                    addr = body.get('addr')
                if is_to_head:
                    self.head = name
                self.links[name] = intra_queue.IntraQueue(self.parent.lord, addr, writer)
                body = {'lord': self.parent.lord, 'name': self.parent.adaptor.name,
                        'addr': {'host': self.host, 'port': self.port}}
                ans = msg_factory.get_msg('intra_linked', body)
                await self.links[name].put(ans)
                if ans.get('command') not in self.parent.adaptor.not_log_commands:
                    logging.debug(log_util.sync_sent_log(self, ans))
                await queue.put(msg_factory.get_msg('ready'))
            elif command == 'intra_linked':
                body = msg.get('body')
                name = None
                lord = None
                addr = None
                if body:
                    name = body.get('name')
                    lord = body.get('lord')
                    addr = body.get('addr')
                self.links[name] = intra_queue.IntraQueue(lord, addr, writer)
                await self.parent.adaptor.notify(msg)
            else:
                recipient = self.clarify_recipient(msg['recipient'])
                if isinstance(recipient, asyncio.Queue):
                    await recipient.put(msg)
                    if msg.get('command') not in self.parent.adaptor.not_log_commands:
                        logging.debug(log_util.async_sent_log(self, msg))

    async def get_intra_queue(self, name):
        res = self.links.get(name)
        if res:
            return res
        msg = msg_factory.get_msg('find_link', {'name': name})
        ans = await self.ask(msg)
        if ans['command'] != 'link_found':
            return
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(
            self.start_client(ans['body']['addr']['host'], ans['body']['addr']['port'], queue, False))
        await queue.get()
        return self.links.get(name)

    async def ask(self, msg):
        entity = f'_{self.parent.connector.ask_index}'
        self.parent.connector.ask_index += 1
        msg['sender'] = {'node': self.parent.adaptor.name, 'entity': entity}
        queue = asyncio.Queue()
        self.parent.connector.asks[entity] = queue
        await self.links[self.head].put(msg)
        if msg.get('command') not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.async_ask_log(self, msg))
        timer.start(queue, msg['mid'], 2)
        ans = await queue.get()
        command = ans.get('command')
        if command == 'timeout':
            logging.warning(log_util.async_received_log(self, ans))
        elif command not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.async_received_log(self, ans))
        if entity is not None:
            del self.parent.connector.asks[entity]
        return ans
