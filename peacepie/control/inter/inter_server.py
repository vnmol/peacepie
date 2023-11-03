import asyncio
import logging

from peacepie import msg_factory, params
from peacepie.assist import log_util, serialization
from peacepie.control.inter import inter_queue


class InterServer:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.system_name = params.instance['system_name']
        self.server = None
        self.host = None
        self.port = None
        self.links = {}
        self.queue = asyncio.Queue()
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def run(self, queue):
        self.host = params.instance['ip']
        self.port = int(params.instance['inter_port'])
        await self.start_server(queue)
        while True:
            msg = await self.queue.get()
            self.logger.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    self.logger.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                self.logger.exception(ex)

    async def handle(self, msg):
        command = msg['command']
        if command == 'inter_register_system':
            await self.inter_register_system(msg)
        elif command == 'inter_connect':
            await self.inter_connect(msg)
        else:
            await self.route(msg)
        return True

    async def start_server(self, queue):
        try:
            self.server = await asyncio.start_server(self.server_handle, self.host, self.port)
            await queue.put(msg_factory.get_msg('ready'))
            self.logger.info(f'{log_util.get_alias(self)} is started on port {self.port}')
        except Exception as ex:
            self.logger.exception(ex)

    async def server_handle(self, reader, writer):
        serializer = serialization.Serializer()
        body = {'system_name': self.system_name, 'addr': {'host': self.host, 'port': self.port}}
        msg = msg_factory.get_msg('inter_link', body)
        msg['mid'] = self.system_name + '.' + msg['mid']
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
                    await self._handle(res, writer)
            except Exception as ex:
                self.logger.exception(ex)
                reader = None

    async def inter_register_system(self, msg):
        system_name = msg['body']['system']['name']
        res = self.links.get(system_name)
        if res:
            await res.close()
        self.links[system_name] = inter_queue.InterQueue(msg['body']['system']['addr'])

    async def inter_connect(self, msg):
        system_name = msg['body']['system_name']
        sender = msg['sender']
        res = self.links.get(system_name)
        if not res:
            if sender:
                self.parent.adaptor.send(msg_factory.get_msg('system_is_not_found', recipient=sender))
            return
        if res.writer:
            return
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.start_client(res, queue))
        await queue.get()

    async def start_client(self, iq, queue):
        reader = None
        writer = None
        try:
            reader, writer = await asyncio.open_connection(iq.addr['host'], iq.addr['port'])
            iq.writer = writer
            self.logger.info(log_util.get_alias(self) + f' Channel to ({iq.addr["host"]}, {iq.addr["port"]}) is opened')
        except Exception as ex:
            self.logger.exception(ex)
        await self.client_handle(iq, reader, writer, queue)

    async def client_handle(self, iq, reader, writer, queue):
        serializer = serialization.Serializer()
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self._handle(res, writer, queue)
            except Exception as ex:
                self.logger.exception(ex)
                reader = None
        await iq.close()

    async def _handle(self, msg, writer, queue=None):
        self.logger.debug(log_util.sync_received_log(self, msg))
        command = msg['command']
        if command == 'inter_link':
            await self.inter_link(msg, writer)
        elif command == 'inter_linked':
            await self.inter_linked(msg, writer, queue)
        else:
            recipient = await self.clarify_recipient(msg['recipient'])
            if not recipient:
                return
            await recipient.put(msg)
            if isinstance(recipient, asyncio.Queue):
                self.logger.debug(log_util.async_sent_log(self, msg))
            else:
                self.logger.debug(log_util.sync_sent_log(self, msg))
        return True

    async def inter_link(self, msg, writer):
        res = self.links.get(msg['body']['system_name'])
        res.writer = writer
        if not res or res.addr != msg['body']['addr']:
            await res.close()
            return
        body = {'system_name': self.system_name, 'addr': {'host': self.host, 'port': self.port}}
        ans = msg_factory.get_msg('inter_linked', body)
        await res.put(ans)
        self.logger.debug(log_util.sync_sent_log(self, ans))

    async def inter_linked(self, msg, writer, queue):
        addr = msg['body'].get('addr')
        res = self.links.get(msg['body']['system_name'])
        if res:
            res.writer = writer
        else:
            return
        if addr:
            if res.addr != addr:
                await res.close()
                return
            ans = msg_factory.get_msg('inter_linked', {'system_name': self.system_name})
            ans['mid'] = self.system_name + '.' + ans['mid']
            await res.put(ans)
            self.logger.debug(log_util.sync_sent_log(self, ans))
        await self.parent.adaptor.notify(msg)
        if queue:
            await queue.put(msg_factory.get_msg('ready'))

    async def route(self, msg):
        res = self.links.get(msg['recipient'].get('system'))
        if msg['sender']:
            if res:
                msg['sender'] = self.parent.connector.add_system(msg['sender'], self.system_name)
            else:
                ans = msg_factory.get_msg('system_is_not_registered', recipient=msg['sender'])
                await self.parent.adaptor.send(ans, self)
                return
        await res.put(msg)
        self.logger.debug(log_util.sync_sent_log(self, msg))

    async def clarify_recipient(self, recipient):
        if type(recipient) is dict:
            node = recipient.get('node')
            if node and node != self.parent.adaptor.name:
                res = await self.parent.intralink.get_intra_queue(node)
                return res
            recipient = recipient['entity']
        if not recipient:
            return self.parent.adaptor.queue
        if type(recipient) is not str:
            return None
        if recipient.startswith('_'):
            res = self.parent.connector.asks[recipient]
            return res
        else:
            if recipient == self.parent.adaptor.name:
                return self.parent.adaptor.queue
            else:
                return self.parent.actor_admin.get_actor_queue(recipient)
