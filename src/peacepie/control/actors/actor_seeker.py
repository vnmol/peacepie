import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util, timer


class ActorSeeker:

    def __init__(self, parent):
        self.parent = parent
        self.queue = asyncio.Queue()
        self.not_log_commands = set()
        self.cumulative_commands = {}
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self):
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

    async def handle(self, msg):
        command = msg['command']
        if command == 'seek_actor':
            await self.seek_actor(msg)
        elif command == 'find_actor':
            await self.find_actor(msg, False)
        else:
            return False
        return True

    async def seek_actor(self, msg):
        if await self.find_actor(msg, True):
            return
        msg['recipient'] = {'node': self.parent.intralink.head, 'entity': None}
        await self.parent.adaptor.send(msg, self)

    async def find_actor(self, msg, is_local):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        entity = body.get('entity')
        res = self.parent.actor_admin.actors.get(entity)
        if res:
            ans_body = {'mid': msg.get('mid'), 'node': self.parent.adaptor.name, 'entity': entity}
            if body.get('with_class_desc'):
                ans_body['class_desc'] = res.get('adaptor').class_desc
            ans = msg_factory.get_msg('actor_is_found', ans_body, recipient=recipient)
            await self.parent.adaptor.send(ans, self)
            return True
        if is_local:
            return False
        ans = msg_factory.get_msg('actor_is_not_found', {'mid': msg.get('mid')}, recipient=recipient)
        await self.parent.adaptor.send(ans, self)
        return False


class HeadActorSeeker:

    def __init__(self, parent):
        self.parent = parent
        self.queue = asyncio.Queue()
        self.not_log_commands = set()
        self.cumulative_commands = {}
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self):
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

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
        recipient = msg.get('sender')
        if len(self.parent.intralink.get_recipients()) == 0:
            ans = msg_factory.get_msg('actor_is_not_found', {'mid': msg.get('mid')}, recipient=recipient)
            await self.parent.adaptor.send(ans, self)
            return
        queue = asyncio.Queue()
        entity = f'_{self.parent.ask_index}'
        self.parent.ask_index += 1
        self.parent.asks[entity] = queue
        sender = {'node': self.parent.adaptor.name, 'entity': entity}
        message = msg_factory.get_msg('find_actor', msg.get('body'), sender=sender)
        count = 0
        for receiver in self.parent.intralink.get_recipients():
            await receiver.put(message)
            count += 1
            logging.debug(log_util.sync_ask_log(self, message))
        timer.start(2, queue, message['mid'])
        while True:
            res = await queue.get()
            count -= 1
            command = res.get('command')
            if command == 'actor_is_found':
                res['recipient'] = recipient
                await self.parent.adaptor.send(res, self)
                del self.parent.asks[entity]
                return
            if command == 'tick' or count == 0:
                break
        del self.parent.asks[entity]
        ans = msg_factory.get_msg('actor_is_not_found', {'mid': msg.get('mid')}, recipient=recipient)
        await self.parent.adaptor.send(ans, self)

    async def find_actor(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        entity = body.get('entity')
        res = self.parent.actor_admin.actors.get(entity)
        if not res:
            return False
        ans_body = {'mid': msg.get('mid'), 'node': self.parent.adaptor.name, 'entity': entity}
        if body.get('with_class_desc'):
            ans_body['class_desc'] = res.get('adaptor').class_desc
        ans = msg_factory.get_msg('actor_is_found', ans_body, recipient=recipient)
        await self.parent.adaptor.send(ans, self)
        return True
