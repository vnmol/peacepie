import asyncio
import logging
import time

from peacepie import msg_factory, params
from peacepie.assist import log_util, serialization
from peacepie.control.inter import inter_queue


class InterServer:

    def __init__(self, parent):
        self.parent = parent
        self.system_name = params.instance['system_name']
        self.server = None
        self.host = None
        self.port = None
        self.links = {}
        self.queue = asyncio.Queue()
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self, queue):
        self.host = params.instance.get('ip')
        self.port = params.instance.get('inter_port')
        await self.start_server(queue)
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'inter_connect':
            await self.inter_connect(msg)
        elif command == 'inter_disconnect':
            await self.inter_disconnect(msg)
        else:
            await self.route(msg)
        return True

    async def start_server(self, queue):
        try:
            self.server = await asyncio.start_server(self.server_handle, self.host, self.port)
            await queue.put(msg_factory.get_msg('ready'))
            logging.info(f'{log_util.get_alias(self)} is started at address ({self.host}:{self.port})')
        except Exception as ex:
            logging.exception(ex)

    async def server_handle(self, reader, writer):
        peer = writer.get_extra_info('socket').getpeername()
        logging.warning(log_util.get_alias(self) + f' Channel to ({peer[0]}, {peer[1]}) is opened')
        serializer = serialization.Serializer()
        body = self.parent.connector.get_addr(self.system_name, self.parent.adaptor.name, None)
        msg = msg_factory.get_msg('inter_link', body)
        writer.write(serializer.serialize(msg))
        await writer.drain()
        logging.debug(log_util.sync_sent_log(self, msg))
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self._handle(res, writer)
            except Exception as ex:
                logging.exception(ex)
                reader = None
        writer.close()
        await writer.wait_closed()
        logging.warning(log_util.get_alias(self) + f' Channel to ({peer[0]}, {peer[1]}) is closed')

    async def inter_connect(self, msg):
        body = msg.get('body')
        addr = body.get('addr')
        host = addr.get('host')
        port = int(addr.get('port'))
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.start_client(host, port, queue))
        ans = await queue.get()
        ans['recipient'] = msg.get('sender')
        await self.parent.adaptor.send(ans)

    async def inter_disconnect(self, msg):
        body = msg.get('body')
        if not body:
            return
        system_name = body.get('system')
        if not system_name:
            return
        link = self.links.get(system_name)
        if not link:
            return
        await link.close()
        del self.links[system_name]
        ans = self.parent.adaptor.get_msg('inter_disconnected', recipient=msg.get('sender'))
        await self.parent.adaptor.send(ans)
        logging.info(log_util.get_alias(self) + f' Channel to system "{system_name}" is closed')

    async def close_writer(self, writer):
        if not writer:
            return
        peer = writer.get_extra_info('socket').getpeername()
        writer.close()
        await writer.wait_closed()
        logging.warning(log_util.get_alias(self) + f' Channel to ({peer[0]}, {peer[1]}) is closed')

    async def start_client(self, host, port, queue):
        t = time.time()
        writer = None
        while True:
            try:
                reader, writer = await asyncio.open_connection(host, port)
                logging.info(log_util.get_alias(self) + f' Channel to ({host}, {port}) is opened')
                await self.client_handle(reader, writer, queue)
            except Exception as ex:
                logging.exception(ex)
            await self.close_writer(writer)
            await asyncio.sleep(1 if time.time() - t < 2 else 60)

    async def client_handle(self, reader, writer, queue):
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
                logging.exception(ex)
                reader = None

    async def _handle(self, msg, writer, queue=None):
        logging.debug(log_util.sync_received_log(self, msg))
        command = msg['command']
        if command == 'inter_link':
            await self.inter_link(msg, writer, queue)
        elif command == 'inter_linked':
            await self.inter_linked(msg, writer, queue)
        else:
            recipient = await self.clarify_recipient(msg['recipient'])
            if not recipient:
                return
            await recipient.put(msg)
            if isinstance(recipient, asyncio.Queue):
                logging.debug(log_util.async_sent_log(self, msg))
            else:
                logging.debug(log_util.sync_sent_log(self, msg))
        return True

    async def inter_link(self, msg, writer, queue):
        res = inter_queue.InterQueue(writer)
        system_addr = msg.get('body')
        system_name = system_addr.get('system')
        self.links[system_name] = res
        body = self.parent.connector.get_addr(self.system_name, self.parent.adaptor.name, None)
        ans = msg_factory.get_msg('inter_linked', body)
        await res.put(ans)
        logging.debug(log_util.sync_sent_log(self, ans))
        msg['command'] = 'inter_linked'
        await self.parent.adaptor.notify(msg)
        if queue:
            await queue.put(msg_factory.get_msg('inter_connected', system_addr))

    async def inter_linked(self, msg, writer, queue):
        res = inter_queue.InterQueue(writer)
        system_addr = msg.get('body')
        system_name = system_addr.get('system')
        self.links[system_name] = res
        await self.parent.adaptor.notify(msg)
        if queue:
            await queue.put(msg_factory.get_msg('inter_connected', system_addr))

    async def route(self, msg):
        res = self.links.get(msg['recipient'].get('system'))
        if msg.get('sender'):
            if res:
                msg['sender'] = self.parent.connector.add_system(msg['sender'], self.system_name)
            else:
                ans = msg_factory.get_msg('system_is_not_registered', recipient=msg['sender'])
                await self.parent.adaptor.send(ans, self)
                return
        await res.put(msg)
        logging.debug(log_util.sync_sent_log(self, msg))

    async def clarify_recipient(self, recipient):
        if type(recipient) is dict:
            node = recipient.get('node')
            if node and node != self.parent.adaptor.name:
                res = await self.parent.intralink.get_intra_queue(node)
                return res
            recipient = recipient.get('entity')
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
