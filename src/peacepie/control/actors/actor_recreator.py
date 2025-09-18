import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util, timer


class ActorRecreator:

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
        if command == 'recreate_actor':
            await self.recreate_actor(msg)
        else:
            return False
        return True

    async def recreate_actor(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        node = body.get('node')
        old_entity = body.get('entity')
        recipient = msg.get('sender')
        timeout = (msg.get('timeout') if msg.get('timeout') else 4) / 2
        is_locally = node == self.grandparent.adaptor.get_node()
        actor = self.parent.actors.get(old_entity)
        if not actor:
            await self.redirect(old_entity, recipient, msg)
            return
        adaptor = actor.get('adaptor')
        body = {'class_desc': adaptor.class_desc, 'name': None if is_locally else old_entity}
        ans = await self.grandparent.adaptor.ask(msg_factory.get_msg('create_replica', body, node), timeout, self)
        if ans.get('command') != 'actor_is_created':
            await self.failure(recipient)
            return
        adaptor.pause()
        new_entity = ans.get('body').get('entity')
        is_idling = await adaptor.is_idling(timeout)
        params = adaptor.get_params()
        try:
            if is_locally:
                self.transit_locally(is_idling, old_entity, new_entity, params)
            else:
                await self.transit_remotely(node, is_idling, new_entity, params, timeout)
        except Exception as e:
            logging.exception(e)
            self.parent.actors[old_entity] = actor
            adaptor.resume()
            return
        await self.stop(actor, timeout)
        if is_locally:
            self.parent.actors.get(old_entity).get('adaptor').resume()
        else:
            msg = msg_factory.get_msg('replica_resume', {'entity': old_entity}, {'node': node, 'entity': None})
            await self.grandparent.adaptor.ask(msg, timeout, self)
        if recipient:
            await self.grandparent.adaptor.send(msg_factory.get_msg('actor_is_recreated', None, recipient), self)

    async def redirect(self, entity, recipient, msg):
        queue = self.grandparent.cache.get(entity)
        if queue:
            msg['recipient'] = None
            await queue.put(msg)
            logging.debug(log_util.sync_sent_log(self, msg))
            return
        ans = await self.grandparent.adaptor.ask(msg_factory.get_msg('seek_actor', {'entity': entity}))
        if ans.get('command') != 'actor_found':
            await self.failure(recipient)
            return
        msg['recipient'] = {'node': ans.get('body').get('node'), 'entity': None}
        await self.grandparent.adaptor.send(msg, self)

    async def failure(self, recipient):
        if not recipient:
            return
        await self.grandparent.adaptor.send(msg_factory.get_msg('actor_is_not_recreated', None, recipient), self)

    def transit_locally(self, is_idling, old_entity, new_entity, params):
        old_actor = self.parent.actors.pop(old_entity)
        old_adaptor = old_actor.get('adaptor')
        new_actor = self.parent.actors.pop(new_entity)
        new_adaptor = new_actor.get('adaptor')
        new_adaptor.name = old_entity
        performer = new_adaptor.performer
        logging.info(f'{performer.__class__.__name__} "{new_entity}"({id(performer)}) has renamed to "{old_entity}"')
        new_adaptor.set_params(params)
        try:
            new_adaptor.queue.put_nowait(msg_factory.get_msg('start'))
            if not is_idling:
                new_adaptor.queue.put_nowait(old_adaptor.msg)
            while True:
                msg = old_adaptor.queue.get_nowait()
                new_adaptor.queue.put_nowait(msg)
        except asyncio.QueueEmpty:
            pass
        if old_adaptor.not_log_commands:
            new_adaptor.not_log_commands.update(old_adaptor.not_log_commands)
        self.parent.actors[old_entity] = new_actor

    async def transit_remotely(self, node, is_idling, entity, params, timeout):
        body = {'entity': entity, 'params': params}
        msg = msg_factory.get_msg('set_replica_params', body, {'node': node, 'entity': None})
        await self.grandparent.adaptor.ask(msg, timeout, self)
        await self.grandparent.add_to_cache(node, [entity])
        new_addr = {'node': node, 'entity': entity}
        msg = msg_factory.get_msg('change_caches', new_addr, self.grandparent.adaptor.get_head_addr())
        await self.grandparent.adaptor.ask(msg, 10, self)
        actor = self.parent.actors.pop(entity)
        adaptor = actor.get('adaptor')
        if adaptor.not_log_commands:
            msg = msg_factory.get_msg('not_log_commands_set', {'commands': list(adaptor.not_log_commands)})
            await self.send_to_clone(node, entity, msg)
        await self.send_to_clone(node, entity, msg_factory.get_msg('start'))
        if not is_idling:
            await self.send_to_clone(node, entity, adaptor.msg)
        while not adaptor.queue.empty():
            await self.send_to_clone(node, entity, await adaptor.queue.get())

    async def send_to_clone(self, node, entity, msg):
        res = msg_factory.get_msg('transit_message', {'entity': entity, 'message': msg}, {'node': node, 'entity': None})
        await self.grandparent.adaptor.send(res, self)

    async def stop(self, actor, timeout):
        adaptor = actor.get('adaptor')
        adaptor.resume(True)
        if not await adaptor.is_stopped(timeout):
            try:
                task = actor.get('task')
                task.cancel()
                await asyncio.wait_for(task, timeout)
            except Exception as e:
                logging.exception(e)
