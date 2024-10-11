import asyncio
import logging

from peacepie import adaptor, msg_factory
from peacepie.assist import log_util, timer

index = 0


class ActorLoader:

    def __init__(self, parent):
        global index
        self.name = f'actor_loader_{index}'
        index += 1
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
        command = msg.get('command')
        if command == 'get_class':
            await self.get_class(msg)
        elif command == 'create_actor' or command == 'clone_actor':
            await self.create_actor(msg)
        elif command == 'create_actors':
            await self.create_actors(msg)
        else:
            return False
        return True

    async def get_class(self, msg):
        clss = await self._get_class(msg)
        ans = msg_factory.get_msg('class', clss, recipient=msg.get('sender'))
        await self.parent.parent.connector.send(self, ans)

    async def create_actor(self, msg):
        body = msg.get('body') if msg.get('body') else {}
        class_desc = body.get('class_desc')
        name = body.get('name')
        if self.parent.actors.get(name):
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
            await self.parent.parent.connector.send(self, answer)
            return
        clss = await self._get_class(msg)
        try:
            adptr = adaptor.Adaptor(class_desc, name, self.parent.parent, clss(), msg.get('sender'))
            if msg.get('command') == 'clone_actor':
                adptr.is_enabled = False
        except Exception as e:
            logging.exception(e)
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
            await self.parent.parent.connector.send(self, answer)
            return
        task = asyncio.get_running_loop().create_task(adptr.run())
        self.parent.actors[name] = {'adaptor': adptr, 'task': task}

    async def create_actors(self, msg):
        clss = await self._get_class(msg)
        queue = asyncio.Queue()
        actors = {}
        body = msg.get('body') if msg.get('body') else {}
        class_desc = body.get('class_desc')
        if not body:
            return
        names = body.get('names')
        if not names:
            return
        for name in names:
            try:
                adptr = adaptor.Adaptor(class_desc, name, self.parent.parent, clss(), queue)
                task = asyncio.get_running_loop().create_task(adptr.run())
                actors[name] = {'adaptor': adptr, 'task': task}
            except Exception as e:
                logging.exception(e)
                await self.clear(actors, msg.get('sender'))
                return
        timeout = msg.get('timeout')
        if not timeout:
            timeout = 1
        timer.start(timeout, queue, msg.get('mid'))
        count = 0
        while True:
            if count == len(actors):
                break
            ans = await queue.get()
            logging.debug(log_util.async_received_log(self, ans))
            if ans.get('command') != 'actor_is_created':
                break
            count += 1
        if count < len(actors):
            await self.clear(actors, msg.get('sender'))
            return
        self.parent.actors.update(actors)
        ans = msg_factory.get_msg('actors_are_created', self.parent.parent.adaptor.name, msg.get('sender'))
        await self.parent.parent.connector.send(self, ans)

    async def clear(self, actors, recipient):
        for actor in actors:
            actor['task'].cancel()
        ans = msg_factory.get_msg('actors_are_not_created', recipient=recipient)
        await self.parent.parent.connector.send(self, ans)

    async def _get_class(self, msg):
        body = msg.get('body')
        if not body:
            return None
        class_desc = body.get('class_desc')
        if not class_desc:
            return None
        if isinstance(class_desc, type):
            return class_desc
        res = self.parent.package_admin.get_class(class_desc, msg.get('timeout'))
        if isinstance(res, type):
            return res
        res = await res.get()
        return res
