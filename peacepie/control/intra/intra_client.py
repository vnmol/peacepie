import asyncio

from peacepie import params, msg_factory
from peacepie.assist import log_util, timer, serialization
from peacepie.control.inter import inter_queue
from peacepie.control.intra.intra_link import IntraLink


class IntraClient(IntraLink):

    async def run(self, queue):
        await self.start_server()
        asyncio.get_running_loop().create_task(
            self.start_client(params.instance['intra_host'], params.instance['intra_port'], queue, True))

    async def start_server(self):
        try:
            self.server = await asyncio.start_server(self.server_handle, self.host, 0)
            self.port = self.server.sockets[0].getsockname()[1]
            self.logger.info(f'{log_util.get_alias(self)} is started on port {self.port}')
        except Exception as ex:
            self.logger.exception(ex)

    async def server_handle(self, reader, writer):
        serializer = serialization.Serializer()
        body = {'name': self.parent.adaptor.name, 'addr': {'host': self.host, 'port': self.port}}
        msg = msg_factory.get_msg('intra_link', body)
        writer.write(serializer.serialize(msg))
        await writer.drain()
        self.logger.debug(log_util.sync_sent_log(self, msg))
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self.handle(res, writer, None)
            except Exception as ex:
                self.logger.exception(ex)
                reader = None

    async def start_client(self, host, port, queue, is_to_head):
        reader = None
        writer = None
        while True:
            try:
                reader, writer = await asyncio.open_connection(host, port)
                self.logger.info(log_util.get_alias(self) + f' Channel to ({host}, {port}) is opened')
            except Exception as ex:
                self.logger.exception(ex)
            await self.client_handle(reader, writer, queue, is_to_head)
            await asyncio.sleep(10)

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
                self.logger.exception(ex)
                reader = None
        if self.head:
            self.logger.info(log_util.get_alias(self) + ' Channel is closed')
            await self.links[self.head].close()
            self.head = None

    async def handle(self, msg, writer, queue, is_to_head=False):
        self.logger.debug(log_util.sync_received_log(self, msg))
        command = msg['command']
        if command == 'intra_link':
            name = msg['body']['name']
            if is_to_head:
                self.head = name
            self.links[name] = inter_queue.InterQueue(msg['body']['addr'], writer=writer)
            body = {'lord': self.parent.lord, 'name': self.parent.adaptor.name,
                    'addr': {'host': self.host, 'port': self.port}}
            ans = msg_factory.get_msg('intra_linked', body)
            await self.links[name].put(ans)
            self.logger.debug(log_util.sync_sent_log(self, ans))
            await queue.put(msg_factory.get_msg('ready'))
        elif command == 'intra_linked':
            self.links[msg['body']['name']] = inter_queue.InterQueue(msg['body']['addr'], writer=writer)
            await self.parent.adaptor.notify(msg)
        else:
            recipient = self.clarify_recipient(msg['recipient'])
            if isinstance(recipient, asyncio.Queue):
                await recipient.put(msg)
                self.logger.debug(log_util.async_sent_log(self, msg))

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
        self.logger.debug(log_util.async_ask_log(self, msg))
        timer.start(queue, msg['mid'], 2)
        ans = await queue.get()
        if ans['command'] == 'timeout':
            self.logger.warning(log_util.async_received_log(self, ans))
        else:
            self.logger.debug(log_util.async_received_log(self, ans))
        if entity is not None:
            del self.parent.connector.asks[entity]
        return ans
