import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util, timer


class ActorMover:

    def __init__(self, parent):
        self.parent = parent
        self.grandparent = parent.parent
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
        command = msg.get('command')
        if command == 'move_actor':
            await self.move_actor(msg)
        else:
            return False
        return True

    async def move_actor(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        node = body.get('node')
        name = body.get('name')
        actor = self.parent.actors.get(name)
        if not actor:
            if recipient:
                await self.grandparent.connector.send(self, msg_factory.get_msg('is_not_moved', None, recipient))
            return
        adaptor = actor.get('adaptor')
        body = {'class_desc': adaptor.class_desc, 'name': adaptor.name}
        ans = await self.grandparent.connector.ask(self, msg_factory.get_msg('clone_actor', body, node), 10)
        if ans.get('command') != 'actor_is_created':
            if recipient:
                await self.grandparent.connector.send(self, msg_factory.get_msg('actor_is_not_moved', None, recipient))
            return
        await self.grandparent.connector.send(self, msg_factory.get_msg('set_availability', {'value': False}, name))
        if hasattr(adaptor.performer, 'exit'):
            try:
                await adaptor.performer.exit()
            except Exception as ex:
                logging.exception(ex)
        await self.grandparent.connector.add_to_cache(node, [name])
        new_addr = {'node': node, 'entity': name}
        query = msg_factory.get_msg('change_cache', new_addr, self.grandparent.adaptor.get_head_addr())
        await self.grandparent.connector.ask(self, query, 10)
        old_addr = {'node': self.grandparent.adaptor.name, 'entity': name}
        await self.grandparent.connector.ask(self, msg_factory.get_control_msg('move', new_addr, old_addr), 10)
        while not adaptor.queue.empty():
            parcel = await adaptor.queue.get()
            parcel['recipient'] = name
            parcel['is_control'] = True
            await self.grandparent.connector.send(self, parcel)
        await self.parent.removing_actor(name)
        await self.grandparent.connector.send(self, msg_factory.get_control_msg('set_availability', {'value': True}, name))
        if recipient:
            await self.grandparent.adaptor.send(self.grandparent.adaptor.get_msg('actor_is_moved', None, recipient))
