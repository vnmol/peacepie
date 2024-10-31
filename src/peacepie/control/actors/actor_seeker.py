import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util, timer


class ActorSeeker:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.queue = asyncio.Queue()
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def run(self):
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
        if command == 'seek_actor':
            await self.seek_actor(msg)
        elif command == 'find_actor':
            await self.find_actor(msg)
        else:
            return False
        return True

    async def seek_actor(self, msg):
        msg['recipient'] = {'node': self.parent.intralink.head, 'entity': None}
        await self.parent.adaptor.send(msg, self)

    async def find_actor(self, msg):
        name = msg['body']['name']
        res = self.parent.actor_admin.actors.get(name)
        if not res or res.get('adaptor').is_clone_prototype:
            return
        body = {'node': self.parent.adaptor.name, 'entity': name}
        message = msg_factory.get_msg('actor_found', body, recipient=msg['sender'])
        await self.parent.adaptor.send(message, self)


class HeadActorSeeker:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.queue = asyncio.Queue()
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def run(self):
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
        if command == 'seek_actor':
            await self.seek_actor(msg)
        elif command == 'find_actor':
            await self.find_actor(msg)
        else:
            return False
        return True

    async def seek_actor(self, msg):
        if await self.find_actor(msg):
            return
        queue = asyncio.Queue()
        entity = f'_{self.parent.ask_index}'
        self.parent.ask_index += 1
        self.parent.asks[entity] = queue
        sender = {'node': self.parent.adaptor.name, 'entity': entity}
        message = msg_factory.get_msg('find_actor', msg['body'], sender=sender)
        for recipient in self.parent.intralink.get_recipients():
            await recipient.put(message)
            self.logger.debug(log_util.sync_ask_log(self, message))
        timer.start(1, queue, message['mid'])
        res = await queue.get()
        del self.parent.asks[entity]
        if res['command'] == 'tick':
            return
        res['recipient'] = msg['sender']
        await self.parent.adaptor.send(res, self)

    async def find_actor(self, msg):
        name = msg['body']['name']
        res = self.parent.actor_admin.actors.get(name)
        if not res or not res.get('adaptor').is_running:
            return False
        body = {'node': self.parent.adaptor.name, 'entity': name}
        message = msg_factory.get_msg('actor_found', body, recipient=msg['sender'])
        await self.parent.adaptor.send(message, self)
        return True
