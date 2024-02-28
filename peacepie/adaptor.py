import asyncio
import logging

from peacepie.assist import log_util, json_util, serialization, dir_operations, terminal_util, thread_util
from peacepie import msg_factory, params
from peacepie.control import ticker_admin


def get_msg(command, body=None, recipient=None, sender=None, is_inter=False):
    return msg_factory.instance.get_msg(command, body, recipient, sender, is_inter)


class Adaptor:

    def __init__(self, name, parent, performer, sender=None):
        self.logger = logging.getLogger()
        self.name = name
        self.parent = parent
        self.performer = performer
        self.sender = sender
        if not hasattr(self.performer, 'adaptor'):
            txt = f'The performer "{name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.performer.adaptor = self
        self.queue = None
        self.is_running = False
        self.ticker_admin = None
        self.observers = {}
        self.logger.info(f'{self.get_alias(self)} is created')

    def get_alias(self, obj=None):
        if not obj:
            obj = self
        return log_util.get_alias(obj)

    async def run(self):
        self.queue = asyncio.Queue()
        if hasattr(self.performer, 'pre_run'):
            try:
                await self.performer.pre_run()
            except Exception as ex:
                self.logger.exception(ex)
        self.is_running = True
        await self.is_running_notification()
        while True:
            try:
                msg = await self.queue.get()
                self.logger.debug(log_util.async_received_log(self.performer, msg))
                if await self.handle(msg):
                    continue
                if await self.performer.handle(msg):
                    await self.notify(msg)
                else:
                    self.logger.warning(self.get_alias() + ' The message is not handled: ' + str(msg))
            except asyncio.exceptions.CancelledError as e:
                break
            except Exception as ex:
                self.logger.exception(ex)

    async def is_running_notification(self):
        if not self.sender:
            return
        system_name = self.get_param('system_name')
        node = self.parent.adaptor.name if self.parent else self.name
        entity = self.name if self.parent else None
        body = self.get_addr(system_name, node, entity)
        msg = msg_factory.get_msg('actor_is_created', body, recipient=self.sender)
        await self.send(msg)

    async def handle(self, msg):
        command = msg['command']
        if command == 'subscribe':
            res = self.observers.get(msg['body']['command'])
            if not res:
                res = []
                self.observers[msg['body']['command']] = res
            res.append(msg['sender'])
        elif command == 'unsubscribe':
            res = self.observers.get(msg['body']['command'])
            if res:
                res.remove(msg['sender'])
        else:
            return False
        return True

    async def notify(self, msg):
        res = self.observers.get(msg['command'])
        if not res:
            return
        for recipient in res:
            await self.send(msg_factory.get_msg('notification', msg, recipient=recipient))

    def json_loads(self, jsn):
        return json_util.json_loads(jsn)

    def json_dumps(self, jsn):
        return json_util.json_dumps(jsn)

    def get_msg(self, command, body=None, recipient=None, sender=None):
        return msg_factory.get_msg(command, body, recipient, sender)

    async def send(self, msg, sender=None):
        if not sender:
            sender = self
        if self.parent:
            await self.parent.connector.send(sender, msg)
        else:
            await self.performer.connector.send(sender, msg)

    async def ask(self, msg, timeout=1):
        return await self.parent.connector.ask(self, msg, timeout)

    def add_ticker(self, period, count=None):
        if not self.ticker_admin:
            self.ticker_admin = ticker_admin.TickerAdmin()
        return self.ticker_admin.add_ticker(self.queue, period, count)

    def add_to_cache(self, node, entity):
        self.parent.connector.add_to_cache(node, entity)

    def get_node(self):
        if self.parent:
            return self.parent.adaptor.name
        else:
            return self.name

    def get_self_addr(self):
        if self.parent:
            return self.get_addr(None, self.parent.adaptor.name, self.name)
        else:
            return self.get_addr(None, self.name, None)

    def get_param(self, param_name):
        return params.instance.get(param_name)

    def get_addr(self, system, node, entity):
        if self.parent:
            return self.parent.connector.get_addr(system, node, entity)
        else:
            return self.performer.connector.get_addr(system, node, entity)

    def get_head_name(self):
        return self.parent.connector.get_head_name()

    def get_head_addr(self):
        return self.parent.connector.get_head_addr()

    def get_prime_name(self):
        return self.parent.connector.get_prime_name()

    def get_prime_addr(self):
        return self.parent.connector.get_prime_addr()

    def get_serializer(self):
        return serialization.Serializer()

    def makedir(self, dirpath, clear=False):
        dir_operations.makedir(dirpath, clear)

    def execute(self, cmd):
        return terminal_util.execute(cmd)

    def sync_as_async(self, sync_function, sync_args=None):
        return thread_util.sync_as_async(sync_function, sync_args)
