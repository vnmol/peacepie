import asyncio
import logging
import signal

from peacepie import params, msg_factory
from peacepie.assist import dir_opers
from peacepie.control.actors import actor_admin, actor_agent, actor_recreator, actor_seeker
from peacepie.control.intra import intra_server, intra_client


ACTOR_ADMIN_COMMANDS = {'get_class', 'create_actor', 'create_actors', 'remove_actor',
                        'get_source_path', 'get_work_path',
                        'recreate_actor', 'create_replica', 'set_replica_params', 'transit_message', 'replica_resume'}

ACTOR_SEEKER_COMMANDS = {'seek_actor', 'find_actor'}

LIBS_PATH = 'libs_path'


class Admin:

    def __init__(self, lord, host_name, process_name, log_desc):
        self.is_head = False
        self.lord = lord
        self.host_name = host_name
        self.process_name = process_name
        self.log_desc = log_desc
        self.adaptor = None
        self.actor_admin = None
        self.asks = {}
        self.ask_index = 0
        self.cache = {}
        self.intralink = None
        self.intra_tasks = []
        self.actor_seeker = None

    def get_prefix(self):
        return f'{self.host_name}.{self.process_name}.'

    async def pre_run(self):
        self.actor_admin = actor_admin.ActorAdmin(self)
        self.actor_admin.actor_recreator = actor_recreator.ActorRecreator(self.actor_admin)
        asyncio.get_running_loop().create_task(self.actor_admin.actor_recreator.run())
        self.actor_admin.actor_agent = actor_agent.ActorAgent(self.actor_admin)
        asyncio.get_running_loop().create_task(self.actor_admin.actor_agent.run())
        if self.is_head:
            self.actor_seeker = actor_seeker.HeadActorSeeker(self)
            self.intralink = intra_server.IntraServer(self)
        else:
            self.actor_seeker = actor_seeker.ActorSeeker(self)
            self.intralink = intra_client.IntraClient(self)
        asyncio.get_running_loop().create_task(self.actor_seeker.run())
        queue = asyncio.Queue()
        self.intra_tasks.append(asyncio.get_running_loop().create_task(self.intralink.run(queue)))
        await queue.get()

    async def quit(self):
        if self.adaptor.stop_event is not None:
            return
        self.adaptor.stop()

    async def exit(self):
        await self.actor_admin.exit()
        await self.intralink.exit()

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command in ACTOR_ADMIN_COMMANDS:
            await self.actor_admin.handle(msg)
        elif command in ACTOR_SEEKER_COMMANDS:
            msg['recipient'] = self.actor_seeker.queue
            await self.adaptor.send(msg)
        elif command == 'remove_process':
            await self.remove_process()
        elif command == 'get_log_desc':
            ans = msg_factory.get_msg('log_desc', self.log_desc, sender)
            await self.adaptor.send(ans)
        elif command == 'change_cache':
            await self.change_cache(body, sender)
        elif command == 'remove_from_cache':
            await self.remove_from_cache(body, sender)
        elif command == 'get_members':
            await self.get_members(msg)
        else:
            return False
        return True

    async def remove_process(self):
        await self.quit()

    async def change_cache(self, body, recipient):
        await self.add_to_cache(body.get('node'), [body.get('entity')], True)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('cache_is_changed', None, recipient))

    async def add_to_cache(self, node, names, is_exists = False):
        if self.adaptor.name == node:
            for name in names:
                if self.cache.get(name):
                    del self.cache[name]
            return
        queue = await self.intralink.get_intra_queue(node)
        if not queue:
            return
        for name in names:
            if is_exists and not self.cache.get(name):
                continue
            self.cache[name] = queue

    async def remove_from_cache(self, body, recipient):
        name = body.get('name')
        if name in self.cache:
            del self.cache[name]
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('removed_from_cache', None, recipient))

    async def get_members(self, msg):
        body = msg.get('body')
        page_size = body.get('page_size')
        level = body.get('level') if body.get('level') else 'prime'
        xid = body.get('id') if body.get('id') else ''
        page = int(xid.split('_')[2]) if xid.startswith('_page_') else 0
        members = []
        back = self.adaptor.name
        if level == 'actors':
            members = self.actor_admin.get_members()
            members = [{'next_level': 'actor', 'recipient': self.adaptor.name, 'id': member} for member in members]
            back = self.lord
        elif level == 'actor':
            members = [{'next_level': None, 'recipient': None, 'id': body.get('id')}]
        body = format_members(level, self.adaptor.name, page_size, page, members)
        body['_back'] = {'next_level': get_prev(level), 'recipient': back, 'id': '_back'}
        body['level'] = level
        ans = self.adaptor.get_msg('members', body, msg.get('sender'))
        await self.adaptor.send(ans)


def format_members(level, recipient, page_size, page, members):
    lng = len(members)
    count = lng // page_size + 1 if lng % page_size > 0 else lng // page_size
    nav = None
    if count > 1:
        members = members[page_size * page: page_size * (page + 1)]
        nav = {'next_level': level, 'recipient': recipient, 'count': count, 'page': page}
    res = {'members': members}
    if nav:
        res['nav'] = nav
    return res


def get_prev(level):
    if level == 'prime':
        return 'head'
    elif level == 'process':
        return 'prime'
    elif level == 'actors':
        return 'process'
    elif level == 'actor':
        return 'actors'
    return None
