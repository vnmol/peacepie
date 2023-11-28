import asyncio
import logging

from peacepie import params, msg_factory, loglistener
from peacepie.assist import dir_operations
from peacepie.control import spy, connector

from peacepie.control.actors import actor_admin, actor_seeker
from peacepie.control.intra import intra_server, intra_client

ACTOR_ADMIN_COMMANDS = {'get_class', 'create_actor', 'create_actors', 'produce_actor', 'actor_destroyed',
                        'get_dependencies'}

SPY_COMMANDS = {'gather_info', 'get_info', 'info'}

ACTOR_SEEKER_COMMANDS = {'seek_actor', 'find_actor'}

LIBS_PATH = 'libs_path'


class Admin:

    def __init__(self, lord, host_name, process_name):
        self.logger = logging.getLogger()
        self.is_head = False
        self.lord = lord
        self.host_name = host_name
        self.process_name = process_name
        self.adaptor = None
        self.actor_admin = None
        self.actors = {}
        self.connector = None
        self.intralink = None
        self.actor_seeker = None
        self.spy = None
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

    async def handle(self, msg):
        command = msg['command']
        if command in ACTOR_ADMIN_COMMANDS:
            await self.actor_admin.handle(msg)
        elif command in SPY_COMMANDS:
            self.spy.handle(msg)
        elif command in ACTOR_SEEKER_COMMANDS:
            msg['recipient'] = self.actor_seeker.queue
            await self.connector.send(self, msg)
        elif command == 'get_log_desc':
            ans = msg_factory.get_msg('log_desc', loglistener.instance.get_log_desc(), msg['sender'])
            await self.connector.send(self, ans)
        else:
            return False
        return True
