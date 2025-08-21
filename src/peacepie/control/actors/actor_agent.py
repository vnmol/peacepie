import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util



class ActorAgent:

    def __init__(self, parent):
        self.parent = parent
        self.grandparent = parent.parent
        self.queue = asyncio.Queue()
        self.queue_storage = {}
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
        command = msg.get('command')
        if command == 'set_replica_params':
            await self.set_replica_params(msg)
        elif command == 'transit_message':
            await self.transit_message(msg)
        elif command == 'replica_resume':
            await self.replica_resume(msg)
        else:
            return False
        return True

    async def set_replica_params(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        entity = body.get('entity')
        params = body.get('params')
        recipient = msg.get('sender')
        actor = self.parent.actors.get(entity)
        adaptor = actor.get('adaptor')
        adaptor.set_params(params)
        if recipient:
            await self.grandparent.adaptor.send(msg_factory.get_msg('replica_params_are_set', None, recipient))

    async def transit_message(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        entity = body.get('entity')
        message = body.get('message')
        storage = self.queue_storage.get(entity)
        if not storage:
            storage = []
            self.queue_storage[entity] = storage
        storage.append(message)

    async def replica_resume(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        entity = body.get('entity')
        recipient = msg.get('sender')
        storage = self.queue_storage.get(entity)
        if not storage:
            storage = []
            self.queue_storage[entity] = storage
        flag = True
        try:
            await self._replica_resume(entity, storage)
        except Exception as e:
            flag = False
            logging.exception(e)
        del self.queue_storage[entity]
        if recipient:
            if flag:
                await self.grandparent.adaptor.send(msg_factory.get_msg('replica_is_resumed', None, recipient))
            else:
                await self.grandparent.adaptor.send(msg_factory.get_msg('replica_is_not_resumed', None, recipient))

    async def _replica_resume(self, entity, storage):
        adaptor = self.parent.actors.get(entity).get('adaptor')
        try:
            while True:
                message = adaptor.queue.get_nowait()
                storage.append(message)
        except asyncio.QueueEmpty:
            pass
        for message in storage:
            adaptor.queue.put_nowait(message)
        adaptor.resume()
