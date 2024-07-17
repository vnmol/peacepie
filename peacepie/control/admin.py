import asyncio
import os
import signal

from peacepie import params, msg_factory
from peacepie.assist import dir_operations
from peacepie.control import spy, connector

from peacepie.control.actors import actor_admin, actor_seeker
from peacepie.control.intra import intra_server, intra_client

ACTOR_ADMIN_COMMANDS = {'get_class', 'create_actor', 'create_actors', 'produce_actor', 'actor_destroyed',
                        'get_dependencies', 'get_source_path'}

SPY_COMMANDS = {'gather_info', 'get_info', 'info'}

ACTOR_SEEKER_COMMANDS = {'seek_actor', 'find_actor'}

LIBS_PATH = 'libs_path'


class Admin:

    def __init__(self, lord, host_name, process_name, log_desc):
        self.is_head = False
        self.is_finalizing = False
        self.lord = lord
        self.host_name = host_name
        self.process_name = process_name
        self.log_desc = log_desc
        self.adaptor = None
        self.actor_admin = None
        self.connector = None
        self.intralink = None
        self.actor_seeker = None
        self.spy = None
        self.not_log_commands = set()
        self.cumulative_commands = {}
        dir_operations.adjust_path(params.instance['package_dir'], self.process_name)

    def get_prefix(self):
        return f'{self.host_name}.{self.process_name}.'

    async def pre_run(self):
        self.spy = spy.Spy(self)
        self.actor_admin = actor_admin.ActorAdmin(self)
        self.connector = connector.Connector(self)
        if self.is_head:
            self.actor_seeker = actor_seeker.HeadActorSeeker(self)
            self.intralink = intra_server.IntraServer(self)
        else:
            self.actor_seeker = actor_seeker.ActorSeeker(self)
            self.intralink = intra_client.IntraClient(self)
        asyncio.get_running_loop().create_task(self.actor_seeker.run())
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.intralink.run(queue))
        await queue.get()
        loop = asyncio.get_running_loop()
        for signal_name in {'SIGINT', 'SIGTERM'}:
            loop.add_signal_handler(
                getattr(signal, signal_name),
                lambda: asyncio.create_task(self.finalize())
            )

    async def finalize(self):
        if self.is_finalizing:
            return
        self.is_finalizing = True
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def exit(self):
        await self.intralink.exit()

    async def handle(self, msg):
        command = msg.get('command')
        if command in ACTOR_ADMIN_COMMANDS:
            await self.actor_admin.handle(msg)
        elif command in SPY_COMMANDS:
            self.spy.handle(msg)
        elif command in ACTOR_SEEKER_COMMANDS:
            msg['recipient'] = self.actor_seeker.queue
            await self.connector.send(self, msg)
        elif command == 'get_log_desc':
            ans = msg_factory.get_msg('log_desc', self.log_desc, msg['sender'])
            await self.connector.send(self, ans)
        elif command == 'get_members':
            await self.get_members(msg)
        else:
            return False
        return True

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
    if level == 'process':
        return 'prime'
    elif level == 'actors':
        return 'process'
    elif level == 'actor':
        return 'actors'
