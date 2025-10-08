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

    async def exit(self):
        tasks = []
        stop_events = []
        for actor in self.actors.values():
            adaptor = actor.get('adaptor')
            adaptor.stop()
            stop_events.append(adaptor.stop_event.wait())
            tasks.append(actor.get('task'))
        try:
            await asyncio.wait_for(asyncio.gather(*stop_events), timeout=0.4)
        except asyncio.TimeoutError:
            pass
        await self.exiting(tasks)
        tasks = [t for t in asyncio.all_tasks()
                 if t is not asyncio.current_task() and t not in self.parent.intralink.tasks]
        if tasks:
            await self.exiting(tasks)

    async def exiting(self, tasks):
        [task.cancel() for task in tasks]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=0.4)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.exception(e)

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
        if await self.removing_actor(name) and recipient:
            await self.parent.adaptor.send(self.parent.adaptor.get_msg('actor_is_removed', body, recipient))
        elif recipient:
            await self.parent.adaptor.send(self.parent.adaptor.get_msg('actor_is_absent', {'name': name}, recipient))

    async def removing_actor(self, name):
        actor = None
        try:
            actor = self.actors.get(name)
        except Exception as e:
            logging.exception(e)
        if not actor:
            return False
        adaptor = actor.get('adaptor')
        alias = log_util.get_alias(adaptor)
        adaptor.stop()
        if not await adaptor.is_stopped(5):
            return False
        new_addr = {'node': None, 'entity': name}
        msg = msg_factory.get_msg('change_caches', new_addr, self.parent.adaptor.get_head_addr())
        if self.parent.is_head:
            await self.parent.change_caches(msg)
        else:
            await self.parent.adaptor.ask(msg, 10, self)
        del self.actors[name]
        logging.info(f'{alias} is removed')
        return True
