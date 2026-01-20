import asyncio
import logging

from peacepie import msg_factory, params
from peacepie.assist import log_util, serialization, timer
from peacepie.control.intra import intra_queue


class IntraLink:

    def __init__(self, parent):
        self.parent = parent
        self.host = params.instance.get('intra_host') if self.parent.is_head else params.instance.get('ip')
        self.port = params.instance.get('intra_port') if self.parent.is_head else 0
        self.server = None
        self.tasks = {}
        self.links = {}
        self.head = None
        logging.info(log_util.get_alias(self) + ' is created')

    async def exit(self):
        tasks = [asyncio.create_task(self.exiting(task)) for task in self.tasks]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), 0.8)
        except Exception as e:
            logging.exception(e)
        try:
            self.server.close()
            await asyncio.wait_for(self.server.wait_closed(), 0.4)
        except Exception as e:
            logging.exception(e)
        logging.info(f'{log_util.get_alias(self)} is stopped on port {self.port}')

    async def exiting(self, task):
        writer = self.tasks.get(task)
        if writer and not writer.is_closing():
            linklog = f' the channel {link_log(writer)} is closing in {task.get_name()}'
            logging.info(f'{log_util.get_alias(self)}: {linklog}')
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=0.4)
            except Exception as e:
                logging.exception(e)
        if task.done():
            logging.info(f'{log_util.get_alias(self)}: the {task.get_name()} already done')
            return
        logging.info(f'{log_util.get_alias(self)}: the {task.get_name()} is cancelling')
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.4)
            logging.info(f'{log_util.get_alias(self)}: the {task.get_name()} was cancelled')
        except Exception as e:
            logging.exception(e)
        logging.info(f'{log_util.get_alias(self)}: the exit for {task.get_name()} completed')

    async def run(self, queue):
        await self.start_server(queue)
        if not self.parent.is_head:
            asyncio.get_running_loop().create_task(
                self.start_client(params.instance['intra_host'], params.instance['intra_port'], queue, True))

    async def start_server(self, queue):
        try:
            self.server = await asyncio.start_server(self.server_read, self.host, self.port)
            self.port = self.server.sockets[0].getsockname()[1]
            logging.info(f'{log_util.get_alias(self)} is started on port {self.port}')
            if self.parent.is_head:
                await queue.put(msg_factory.get_msg('ready'))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.exception(e)

    async def server_read(self, reader, writer):
        linklog = f' the channel {link_log(writer)} was created in {asyncio.current_task().get_name()}'
        logging.info(f'{log_util.get_alias(self)}: {linklog}')
        self.tasks[asyncio.current_task()] = writer
        serializer = serialization.Serializer()
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
                    await self.server_handle(res, writer)
            except Exception as ex:
                logging.exception(ex)
                reader = None
        linklog = f' the channel {link_log(writer)} was destroyed in {asyncio.current_task().get_name()}'
        del self.tasks[asyncio.current_task()]
        writer.close()
        await writer.wait_closed()
        logging.info(f'{log_util.get_alias(self)}: {linklog}')

    async def server_handle(self, msgs, writer):
        for msg in msgs:
            command = msg.get('command')
            if command not in self.parent.adaptor.not_log_commands:
                logging.debug(log_util.sync_received_log(self, msg))
            if command == 'intra_linked':
                await self.intra_linked(msg, writer)
            elif command == 'find_link':
                await self.find_link(msg, writer)
            else:
                recipient = self.clarify_recipient(msg.get('recipient'))
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
        writer.write(serialization.Serializer.serialize(ans))
        await writer.drain()
        if ans.get('command') not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.sync_sent_log(self, ans))

    def clarify_recipient(self, recipient):
        if recipient is None:
            return self.parent.adaptor.queue
        if type(recipient) is dict:
            system_name = recipient.get('system')
            if system_name and system_name != self.parent.adaptor.get_param('system_name'):
                if self.parent.is_head:
                    return self.parent.interlink.queue
                else:
                    return self.links.get(self.head)
            else:
                recipient = recipient.get('entity')
                if not recipient:
                    return self.parent.adaptor.queue
        if type(recipient) is not str:
            return None
        if recipient.startswith('_'):
            res = self.parent.asks.get(recipient)
            return res
        else:
            if recipient == self.parent.adaptor.name:
                return self.parent.adaptor.queue
            else:
                return self.parent.actor_admin.get_actor_queue(recipient)

    async def start_client(self, host, port, queue, is_to_head):
        while True:
            try:
                reader, writer = await asyncio.open_connection(host, port)
                await self.client_read(reader, writer, queue, is_to_head)
            except asyncio.CancelledError:
                return
            except Exception as ex:
                logging.exception(ex)
            try:
               await asyncio.sleep(10)
            except asyncio.CancelledError:
                return

    async def client_read(self, reader, writer, queue, is_to_head):
        linklog = f' the channel {link_log(writer)} was created in {asyncio.current_task().get_name()}'
        logging.info(f'{log_util.get_alias(self)}: {linklog}')
        self.tasks[asyncio.current_task()] = writer
        serializer = serialization.Serializer()
        while reader:
            if reader.at_eof():
                break
            try:
                data = await reader.read(255)
                res = serializer.deserialize(data)
                if res:
                    await self.client_handle(res, writer, queue, is_to_head)
            except asyncio.CancelledError:
                pass
            except Exception as ex:
                logging.exception(ex)
                reader = None
        linklog = f' the channel {link_log(writer)} was destroyed in {asyncio.current_task().get_name()}'
        del self.tasks[asyncio.current_task()]
        writer.close()
        await writer.wait_closed()
        logging.info(f'{log_util.get_alias(self)}: {linklog}')

    async def client_handle(self, msgs, writer, queue, is_to_head=False):
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
                recipient = self.clarify_recipient(msg.get('recipient'))
                if isinstance(recipient, asyncio.Queue):
                    await recipient.put(msg)
                    if msg.get('command') not in self.parent.adaptor.not_log_commands:
                        logging.debug(log_util.async_sent_log(self, msg))

    async def get_intra_queue(self, name):
        res = self.links.get(name)
        if res:
            return res
        if self.head is None:
            return None
        msg = msg_factory.get_msg('find_link', {'name': name})
        ans = await self.ask(msg)
        if ans['command'] != 'link_found':
            return None
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(
            self.start_client(ans['body']['addr']['host'], ans['body']['addr']['port'], queue, False))
        await queue.get()
        return self.links.get(name)

    def get_recipients(self):
        res = [link for link in self.links.values()]
        return res

    async def ask(self, msg):
        entity = f'_{self.parent.ask_index}'
        self.parent.ask_index += 1
        msg['sender'] = {'node': self.parent.adaptor.name, 'entity': entity}
        queue = asyncio.Queue()
        self.parent.asks[entity] = queue
        await self.links[self.head].put(msg)
        if msg.get('command') not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.sync_ask_log(self, msg))
        timer.start(2, queue, msg['mid'])
        ans = await queue.get()
        command = ans.get('command')
        if command == 'timeout':
            logging.warning(log_util.async_received_log(self, ans))
        elif command not in self.parent.adaptor.not_log_commands:
            logging.debug(log_util.sync_received_log(self, ans))
        if entity is not None:
            del self.parent.asks[entity]
        return ans

    def get_members(self):
        res = [link[0] for link in self.links.items() if not link[1].lord]
        if not self.parent.lord:
            res.append(self.parent.adaptor.name)
        res.sort()
        return res

    def get_all_nodes(self):
        res = [key for key in self.links]
        res.insert(0, self.parent.adaptor.name)
        return res


def link_log(writer):
    return f'{writer.get_extra_info("sockname")}<=>{writer.get_extra_info("peername")}'
