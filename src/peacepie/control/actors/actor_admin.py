import asyncio
import logging

from peacepie.assist import log_util
from peacepie.control.actors import actor_loader, package_admin

LOADER_COMMANDS = {'get_class', 'create_actor', 'create_actors', 'clone_actor'}
MOVER_COMMANDS = {'move_actor'}


class ActorAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.package_admin = package_admin.PackageAdmin(self)
        self.actor_mover = None
        self.actor_loaders = []
        self.actors = {}
        logging.info(log_util.get_alias(self) + ' is created')

    async def handle(self, msg):
        command = msg.get('command')
        if command in LOADER_COMMANDS:
            for loader in self.actor_loaders:
                if loader['loader'].queue.qsize() < 10:
                    await loader['loader'].queue.put(msg)
                    logging.debug(log_util.async_sent_log(self, msg))
                    return True
            loader = self.add_actor_loader()
            await loader.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        elif command in MOVER_COMMANDS:
            await self.actor_mover.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        elif command == 'remove_actor':
            await self.remove_actor(msg)
        elif command == 'get_source_path':
            body = {'path': self.package_admin.source_path}
            ans = self.parent.adaptor.get_msg('source_path', body, recipient=msg.get('sender'))
            await self.parent.adaptor.send(ans)
        else:
            return False
        return True

    def add_actor_loader(self):
        loader = actor_loader.ActorLoader(self)
        task = asyncio.get_running_loop().create_task(loader.run())
        self.actor_loaders.append({'loader': loader, 'task': task})
        return loader

    def get_actor_queue(self, name, is_control):
        actor = self.actors.get(name)
        if not actor:
            return None
        adaptor = actor.get('adaptor')
        if not adaptor:
            return None
        if is_control:
            return adaptor.control_queue
        else:
            return adaptor.queue

    def get_members(self):
        res = [actor for actor in self.actors if self.actors.get(actor).get('adaptor').is_enabled]
        res.sort()
        res.insert(0, self.parent.adaptor.name)
        return res

    async def remove_actor(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        name = body.get('name')
        if not name:
            if recipient:
                await self.parent.adaptor.send(self.parent.adaptor.get_msg('actor_is_absent', body, recipient))
            return
        if await self.removing_actor(name):
            await self.parent.adaptor.send(self.parent.adaptor.get_msg('actor_is_removed', body, recipient))
        else:
            await self.parent.adaptor.send(self.parent.adaptor.get_msg('actor_is_absent', {'name': name}, recipient))


    async def removing_actor(self, name):
        actor = None
        try:
            actor = self.actors.get(name)
        except Exception as e:
            logging.exception(e)
        if not actor:
            return False
        alias = log_util.get_alias(actor.get('adaptor'))
        task = actor.get('task')
        task.cancel()
        await task
        del self.actors[name]
        logging.info(f'{alias} is removed')
        return True

    async def move_actor(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        node = body.get('node')
        name = body.get('name')
        actor = self.actors.get(name)
        if not actor:
            if recipient:
                await self.parent.adaptor.send(self.parent.adaptor.get_msg('is_not_moved', None, recipient))
            return
        adptr = actor.get('adaptor')
        if not await self.clone_actor(node, name, adptr):
            if recipient:
                await self.parent.adaptor.send(self.parent.adaptor.get_msg('is_not_moved', None, recipient))
            return
        await self.removing_actor(name)
        # await self.parent.adaptor.send(self.parent.adaptor.get_msg('is_enabled', recipient=ans.get('body')))
        if recipient:
            await self.parent.adaptor.send(self.parent.adaptor.get_msg('is_moved', None, recipient))

    async def clone_actor(self, node, name, adptr):
        adptr.is_enabled = False
        semaphore = {'up': asyncio.Queue(), 'down': asyncio.Queue()}
        adptr.semaphore = semaphore
        if adptr.queue.qsize() == 0:
            msg = self.parent.adaptor.get_msg('empty')
            await adptr.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        await semaphore.get('up').get()
        query = self.parent.adaptor.get_msg('clone_actor', {'class_desc': adptr.class_desc, 'name': name}, node)
        ans = await self.parent.adaptor.ask(query, 30)
        res = ans.get('command') == 'actor_is_created'
        await semaphore.get('down').put('exit' if res else 'resume')
        body = {'name': name, 'old': adptr.get_self_addr().get('node'), 'new': node}
        msg = self.parent.adaptor.get_msg('change_cache', body, self.parent.adaptor.get_head_addr())
        await self.parent.adaptor.ask(msg, 10)
        return res
