import asyncio
import logging

from peacepie import msg_factory, params
from peacepie.assist import log_util, timer
from peacepie.control.intra import intra_queue

EXCLUSION_COMMANDS = {'create_process'}


class Connector:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.asks = {}
        self.ask_index = 0
        self.cache = {}
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def clarify_recipient(self, recipient):
        if recipient is None:
            return self.parent.adaptor.queue
        if type(recipient) is dict:
            system_name = recipient.get('system')
            if system_name and system_name != params.instance['system_name']:
                head = self.get_head_name()
                if head == self.parent.adaptor.name:
                    return self.parent.interlink.queue
                else:
                    return await self.parent.intralink.get_intra_queue(head)
            if recipient['node'] == self.parent.adaptor.name:
                if recipient['entity']:
                    recipient = recipient['entity']
                else:
                    return self.parent.adaptor.queue
            else:
                return await self.parent.intralink.get_intra_queue(recipient['node'])
        if type(recipient) is str:
            if recipient == self.parent.adaptor.name:
                return self.parent.adaptor.queue
            elif recipient.startswith('_'):
                return self.asks.get(recipient)
            else:
                res = await self.parent.intralink.get_intra_queue(recipient)
                if res:
                    return res
                res = self.parent.actor_admin.get_actor_queue(recipient)
                if not res:
                    res = self.cache.get(recipient)
                return res
        else:
            return recipient

    async def send(self, sender, msg):
        recipient = msg['recipient']
        res = await self.clarify_recipient(recipient)
        if not res:
            self.find_and_send(sender, msg)
            return
        if isinstance(res, asyncio.Queue):
            await res.put(msg)
            self.logger.debug(log_util.async_sent_log(sender, msg))
        else:
            if type(recipient) is not str and type(recipient) is not dict:
                msg['recipient'] = None
            await res.put(msg)
            self.logger.debug(log_util.sync_sent_log(sender, msg))

    async def ask(self, sender, msg, timeout=1):
        recipient = msg['recipient']
        res = await self.clarify_recipient(recipient)
        if not res:
            res = await self.find(sender, recipient)
            if not res:
                return
        msg['timeout'] = timeout
        queue = asyncio.Queue()
        entity = f'_{self.ask_index}'
        self.ask_index += 1
        msg['sender'] = {'node': self.parent.adaptor.name, 'entity': entity}
        self.asks[entity] = queue
        if type(recipient) is not str and type(recipient) is not dict:
            msg['recipient'] = None
        await res.put(msg)
        if isinstance(res, asyncio.Queue):
            self.logger.debug(log_util.async_ask_log(sender, msg))
        else:
            self.logger.debug(log_util.sync_ask_log(sender, msg))
        timer.start(queue, msg['mid'], timeout)
        ans = await queue.get()
        if ans['command'] == 'timeout':
            self.logger.warning(log_util.async_received_log(sender, ans))
        else:
            self.logger.debug(log_util.async_received_log(sender, ans))
        if entity:
            del self.asks[entity]
        return ans

    def find_and_send(self, sender, msg):
        asyncio.get_running_loop().create_task(self._find_and_send(sender, msg))

    async def _find_and_send(self, sender, msg):
        recipient = await self.find(sender, msg['recipient'])
        if not recipient:
            return
        await recipient.put(msg)
        self.logger.debug(log_util.sync_sent_log(sender, msg))

    async def find(self, sender, name):
        res = None
        msg = msg_factory.get_msg('seek_actor', {'name': name})
        ans = await self.ask(sender, msg)
        if ans['command'] == 'actor_found':
            res = await self.parent.intralink.get_intra_queue(ans['body']['node'])
            if res:
                self.cache[name] = res
            else:
                self.logger.warning(f'The actor "{name}" is not found')
        return res

    def get_addr(self, system, node, entity):
        if system:
            return {'system': system, 'node': node, 'entity': entity}
        else:
            return {'node': node, 'entity': entity}

    def add_system(self, addr, system_name):
        return self.get_addr(system_name, addr['node'], addr['entity'])

    def get_head_name(self):
        if self.parent.intralink.head:
            return self.parent.intralink.head
        else:
            return self.parent.adaptor.name

    def get_head_addr(self):
        return self.get_addr(None, self.get_head_name(), None)

    def get_prime_name(self):
        if self.parent.lord:
            return self.parent.lord
        else:
            return self.parent.adaptor.name

    def get_prime_addr(self):
        return self.get_addr(None, self.get_prime_name(), None)
