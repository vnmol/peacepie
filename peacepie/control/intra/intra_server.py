import asyncio

from peacepie import params, msg_factory
from peacepie.assist import log_util
from peacepie.assist.serialization import Serializer
from peacepie.control.intra.intra_link import IntraLink

from peacepie.control.intra import intra_queue


class IntraServer(IntraLink):

    async def run(self, queue):
        await self.start_server(queue)

    async def start_server(self, queue):
        self.host = params.instance['intra_host']
        self.port = params.instance['intra_port']
        try:
            self.server = await asyncio.start_server(self.server_handle, self.host, self.port)
            await queue.put(msg_factory.get_msg('ready'))
            self.logger.info(f'{log_util.get_alias(self)} is started on port {self.port}')
        except Exception as ex:
            self.logger.exception(ex)

    async def server_handle(self, reader, writer):
        serializer = Serializer()
        body = {'lord': self.parent.lord, 'name': self.parent.adaptor.name,
                'addr': {'host': self.host, 'port': self.port}}
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
                    await self.handle(res, writer)
            except Exception as ex:
                self.logger.exception(ex)
                reader = None

    async def handle(self, msg, writer):
        self.logger.debug(log_util.sync_received_log(self, msg))
        command = msg['command']
        if command == 'intra_linked':
            await self.intra_linked(msg, writer)
        elif command == 'find_link':
            await self.find_link(msg, writer)
        else:
            recipient = self.clarify_recipient(msg['recipient'])
            if isinstance(recipient, asyncio.Queue):
                await recipient.put(msg)
                self.logger.debug(log_util.async_sent_log(self, msg))

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
        self.logger.debug(log_util.sync_sent_log(self, ans))

    async def get_intra_queue(self, name):
        res = self.links.get(name)
        return res

    def get_recipients(self):
        res = [link for link in self.links.values()]
        return res
