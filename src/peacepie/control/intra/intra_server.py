import asyncio
import logging

from peacepie import params, msg_factory
from peacepie.assist import log_util
from peacepie.assist.serialization import Serializer
from peacepie.control.intra.intra_link import IntraLink

from peacepie.control.intra import intra_queue


class IntraServer(IntraLink):

    def __init__(self, parent):
        super().__init__(parent)
        self.connections = []

    async def run(self, queue):
        await self.start_server(queue)

    async def start_server(self, queue):
        self.host = params.instance.get('intra_host')
        self.port = params.instance.get('intra_port')
        try:
            self.server = await asyncio.start_server(self.server_handle, self.host, self.port)
            port = self.server.sockets[0].getsockname()[1]
            if port != self.port:
                logging.info(f'Server intra port was changed from {self.port} to {port}!')
                self.port = port
                params.instance['intra_port'] = port
            await queue.put(msg_factory.get_msg('ready'))
            logging.info(f'{log_util.get_alias(self)} is started on port {self.port}')
        except Exception as ex:
            logging.exception(ex)

    async def exit(self):
        for conn in self.connections:
            conn.close()
            await conn.wait_closed()
        self.server.close()
        await self.server.wait_closed()
        logging.info(f'IntraServer on port {self.port} is closed')

    async def server_handle(self, reader, writer):
        self.connections.append(writer)
        serializer = Serializer()
        body = {'lord': self.parent.lord, 'name': self.parent.adaptor.name,
                'addr': {'host': self.host, 'port': self.port}}
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
                    await self.handle(res, writer)
            except Exception as ex:
                logging.exception(ex)
                reader = None
        writer.close()
        await writer.wait_closed()
        self.connections.remove(writer)

    async def handle(self, msgs, writer):
        for msg in msgs:
            command = msg.get('command')
            if command not in self.parent.adaptor.not_log_commands:
                logging.debug(log_util.sync_received_log(self, msg))
            if command == 'intra_linked':
                await self.intra_linked(msg, writer)
            elif command == 'find_link':
                await self.find_link(msg, writer)
            else:
                recipient = self.clarify_recipient(msg.get('recipient'), command == 'is_enabled')
                if isinstance(recipient, asyncio.Queue):
                    await recipient.put(msg)
                    if command not in self.parent.adaptor.not_log_commands:
                        logging.debug(log_util.async_sent_log(self, msg))

    async def intra_linked(self, msg, writer):
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

    async def find_link(self, msg, writer):
        link = self.links.get(msg['body']['name'])
        if link:
            ans = msg_factory.get_msg('link_found', {'addr': link.addr}, recipient=msg['sender'])
        else:
            ans = msg_factory.get_msg('link_not_found', recipient=msg['sender'])
        writer.write(Serializer.serialize(ans))
        await writer.drain()
        if ans.get('command') not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.sync_sent_log(self, ans))

    async def get_intra_queue(self, name):
        res = self.links.get(name)
        return res

    def get_recipients(self):
        res = [link for link in self.links.values()]
        return res
