import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util
from peacepie.control.actors import actor_loader, package_admin

LOADER_COMMANDS = {'get_class', 'create_actor', 'create_replica', 'create_actors'}
RECREATE_COMMANDS = {'recreate_actor'}
AGENT_COMMANDS = {'set_replica_params', 'transit_message', 'replica_resume'}


class ActorAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.package_admin = package_admin.PackageAdmin(self)
        self.actor_recreator = None
        self.actor_agent = None
        self.actor_loaders = []
        self.actors = {}
        self.not_log_commands = set()
        self.cumulative_commands = {}
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
        elif command in RECREATE_COMMANDS:
            await self.actor_recreator.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        elif command in AGENT_COMMANDS:
            await self.actor_agent.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
        elif command == 'remove_actor':
            await self.remove_actor(msg)
        elif command == 'get_source_path':
            body = {'path': self.package_admin.source_path}
            ans = self.parent.adaptor.get_msg('source_path', body, recipient=msg.get('sender'))
            await self.parent.adaptor.send(ans)
        elif command == 'get_work_path':
            body = {'path': self.package_admin.work_path}
            ans = self.parent.adaptor.get_msg('work_path', body, recipient=msg.get('sender'))
            await self.parent.adaptor.send(ans)
        else:
            return False
        return True

    def add_actor_loader(self):
        loader = actor_loader.ActorLoader(self)
        task = asyncio.get_running_loop().create_task(loader.run())
        self.actor_loaders.append({'loader': loader, 'task': task})
        return loader

    def get_actor_queue(self, name):
        actor = self.actors.get(name)
        if not actor:
            return None
        adaptor = actor.get('adaptor')
        if not adaptor:
            return None
        return adaptor.queue

    def get_members(self):
        res = [actor for actor in self.actors]
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
        if self.parent.cache.get(name):
            del self.parent.cache[name]
        logging.info(f'{alias} is removed')
        return True
