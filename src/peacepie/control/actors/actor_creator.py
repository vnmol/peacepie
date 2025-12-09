import asyncio
import logging
import multiprocessing
import importlib.metadata
import os

from peacepie import adaptor, msg_factory, params

from peacepie.assist import auxiliaries, dir_opers, log_util, timer, version

index = 0
replica_index = 0

shared_folders = {'__pycache__', 'bin'}


class VersionError(Exception):
    pass


class ActorCreator:

    def __init__(self, parent):
        global index
        self.name = f'actor_creator_{index}'
        index += 1
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
        if command == 'create_actor':
            await self.create_actor(msg, False)
        elif command == 'create_replica':
            await self.create_actor(msg, True)
        elif command == 'create_actors':
            await self.create_actors(msg)
        else:
            return False
        return True

    async def redirect(self, msg):
        sender = msg.get('sender')
        if msg.get('body').get('is_only'):
            await self.inform('actor_is_not_created', sender)
            return None
        msg.get('body')['is_only'] = True
        nodes = await self.grandparent.adaptor.get_local_nodes(exclude_current=True)
        for node in nodes:
            msg['recipient'] = node
            ans = await self.grandparent.adaptor.ask(msg, questioner=self)
            if ans.get('command') == 'actor_is_created':
                await self.inform('actor_is_created', sender)
                return None
        query = msg_factory.get_msg('create_process', None, self.grandparent.adaptor.get_head_addr())
        ans = await self.grandparent.adaptor.ask(query)
        if ans.get('command') != 'actor_is_created':
            return None
        msg['recipient'] = ans.get('body')
        ans = await self.grandparent.adaptor.ask(msg, questioner=self)
        await self.inform(ans.get('command'), sender)
        return None

    async def inform(self, command, recipient):
        if recipient is None:
            return
        await self.grandparent.adaptor.send(msg_factory.get_msg(command, None, recipient), self)

    async def create_actor(self, msg, is_replica):
        global replica_index
        body = msg.get('body') if msg.get('body') else {}
        class_desc = body.get('class_desc')
        name = body.get('name')
        if self.parent.actors.get(name) and not is_replica:
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
            await self.grandparent.adaptor.send(answer, self)
            return
        real_name = name
        if is_replica and name is None:
            real_name = (f'replica_{self.grandparent.adaptor.get_param("host_name")}_'
                         f'{multiprocessing.current_process().name}_{replica_index}')
            replica_index += 1
        try:
            if isinstance(class_desc, type):
                clss = class_desc
            else:
                clss = await self.grandparent.adaptor.get_class(class_desc)
            if not clss:
                answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
                await self.grandparent.adaptor.send(answer, self)
                return
            adptr = adaptor.Adaptor(class_desc, real_name, self.grandparent, clss(), msg.get('sender'))
            if is_replica:
                adptr.pause_event = asyncio.Event()
        except Exception as e:
            logging.exception(e)
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
            await self.grandparent.adaptor.send(answer, self)
            return
        task = asyncio.get_running_loop().create_task(adptr.run())
        self.parent.actors[real_name] = {'adaptor': adptr, 'task': task}

    async def create_actors(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body') if msg.get('body') else {}
        class_desc = body.get('class_desc')
        clss = await self.grandparent.adaptor.get_class(class_desc)
        if not clss:
            await self.actors_are_not_created(recipient)
            return
        queue = asyncio.Queue()
        actors = {}
        if not body:
            await self.actors_are_not_created(recipient)
            return
        names = body.get('names')
        if not names:
            await self.actors_are_not_created(recipient)
            return
        for name in names:
            try:
                adptr = adaptor.Adaptor(class_desc, name, self.grandparent, clss(), queue)
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
        node = self.grandparent.adaptor.name
        body = {'node': node, 'names': names}
        ans = msg_factory.get_msg('actors_are_created', body, msg.get('sender'))
        await self.grandparent.adaptor.send(ans, self)

    async def clear(self, actors, recipient):
        for actor in actors:
            actor['task'].cancel()
        await self.actors_are_not_created(recipient)

    async def actors_are_not_created(self, recipient):
        ans = msg_factory.get_msg('actors_are_not_created', recipient=recipient)
        await self.grandparent.adaptor.send(ans, self)
