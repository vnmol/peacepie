import asyncio
import logging

from peacepie.assist import log_util
from peacepie.control.actors import actor_loader, package_admin


class ActorAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.package_admin = package_admin.PackageAdmin(self)
        self.actor_loaders = []
        self.actors = {}
        logging.info(log_util.get_alias(self) + ' is created')

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'create_actor' or command == 'create_actors':
            for loader in self.actor_loaders:
                if loader['loader'].queue.qsize() < 10:
                    await loader['loader'].queue.put(msg)
                    logging.debug(log_util.async_sent_log(self, msg))
                    return True
            loader = self.add_actor_loader()
            await loader.queue.put(msg)
            logging.debug(log_util.async_sent_log(self, msg))
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

    def get_actor_queue(self, name):
        actor = self.actors.get(name)
        if actor is None:
            return None
        return actor['adaptor'].queue

    def get_members(self):
        res = [actor for actor in self.actors]
        res.append(self.parent.adaptor.name)
        res.sort()
        return res
