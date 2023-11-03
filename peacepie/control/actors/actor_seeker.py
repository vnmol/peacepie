import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util, timer


class ActorSeeker:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.queue = asyncio.Queue()
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
        sender = msg['sender']
        msg['recipient'] = {'node': self.parent.intralink.head, 'entity': None}
        ans = await self.parent.connector.ask(self, msg)
        if ans:
            ans['recipient'] = sender
            await self.parent.connector.send(self, ans)

    async def find_actor(self, msg):
        name = msg['body']['name']
        res = self.parent.actor_admin.actors.get(name)
        if not res:
            return
        body = {'node': self.parent.adaptor.name, 'entity': name}
        message = msg_factory.get_msg('actor_found', body, recipient=msg['sender'])
        await self.parent.connector.send(self, message)


class HeadActorSeeker:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.queue = asyncio.Queue()
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
        entity = f'_{self.parent.connector.ask_index}'
        self.parent.connector.ask_index += 1
        self.parent.connector.asks[entity] = queue
        sender = {'node': self.parent.adaptor.name, 'entity': entity}
        message = msg_factory.get_msg('find_actor', msg['body'], sender=sender)
        for recipient in self.parent.intralink.get_recipients():
            await recipient.put(message)
            self.logger.debug(log_util.sync_ask_log(self, message))
        timer.start(queue, message['mid'], 1)
        res = await queue.get()
        del self.parent.connector.asks[entity]
        if res['command'] == 'tick':
            return
        res['recipient'] = msg['sender']
        await self.parent.connector.send(self, res)

    async def find_actor(self, msg):
        name = msg['body']['name']
        res = self.parent.actor_admin.actors.get(name)
        if not res:
            return False
        body = {'node': self.parent.adaptor.name, 'entity': name}
        message = msg_factory.get_msg('actor_found', body, recipient=msg['sender'])
        await self.parent.connector.send(self, message)
        return True
