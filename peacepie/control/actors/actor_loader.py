import asyncio
import logging

from peacepie import adaptor, msg_factory
from peacepie.assist import log_util, timer

index = 0


class ActorLoader:

    def __init__(self, parent):
        global index
        self.logger = logging.getLogger()
        self.name = f'actor_loader_{index}'
        index += 1
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
        if command == 'get_class':
            await self.get_class(msg)
        elif command == 'create_actor':
            await self.create_actor(msg)
        elif command == 'create_actors':
            await self.create_actors(msg)
        else:
            return False
        return True

    async def get_class(self, msg):
        clss = self._get_class(msg)
        answer = msg_factory.get_msg('class', clss, recipient=msg['sender'])
        await self.parent.parent.connector.send(self, answer)

    async def create_actor(self, msg):
        clss = await self._get_class(msg)
        name = msg['body']['name']
        try:
            adptr = adaptor.Adaptor(name, self.parent.parent, clss(), msg['sender'])
        except Exception as e:
            self.logger.exception(e)
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg['sender'])
            await self.parent.parent.connector.send(self, answer)
            return
        task = asyncio.get_running_loop().create_task(adptr.run())
        self.parent.actors[name] = {'adaptor': adptr, 'task': task}

    async def create_actors(self, msg):
        clss = await self._get_class(msg)
        queue = asyncio.Queue()
        actors = {}
        for name in msg['body']['names']:
            try:
                adptr = adaptor.Adaptor(name, self.parent.parent, clss(), queue)
                task = asyncio.get_running_loop().create_task(adptr.run())
                actors[name] = {'adaptor': adptr, 'task': task}
            except Exception as e:
                self.logger.exception(e)
                await self.clear(actors, msg['sender'])
                return
        timer.start(queue, msg['mid'], msg['timeout'])
        count = 0
        while True:
            if count == len(actors):
                break
            ans = await queue.get()
            self.logger.debug(log_util.async_received_log(self, ans))
            if ans['command'] != 'actor_is_created':
                break
            count += 1
        if count < len(actors):
            await self.clear(actors, msg['sender'])
            return
        self.parent.actors.update(actors)
        ans = msg_factory.get_msg('actors_are_created', self.parent.parent.adaptor.name, recipient=msg['sender'])
        await self.parent.parent.connector.send(self, ans)

    async def clear(self, actors, recipient):
        for actor in actors:
            actor['task'].cancel()
        ans = msg_factory.get_msg('actors_are_not_created', recipient=recipient)
        await self.parent.parent.connector.send(self, ans)

    async def _get_class(self, msg):
        class_desc = msg['body']['class_desc']
        if isinstance(class_desc, type):
            return class_desc
        res = self.parent.package_admin.get_class(class_desc)
        if isinstance(res, type):
            return res
        return await res.get()
