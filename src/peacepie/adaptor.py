import asyncio
import inspect
import logging

from peacepie.assist import log_util, json_util, serialization, dir_operations, terminal_util, thread_util, timer
from peacepie import msg_factory, params
from peacepie.control import ticker_admin, series_admin
from peacepie.control.head_prime_admin import HeadPrimeAdmin

ADAPTOR_COMMANDS = {'exit', 'subscribe', 'unsubscribe', 'not_log_commands_set', 'not_log_commands_remove',
                    'cumulative_commands_set', 'cumulative_commands_remove', 'cumulative_tick'}


def get_msg(command, body=None, recipient=None, sender=None, is_inter=False):
    return msg_factory.instance.get_msg(command, body, recipient, sender, is_inter)


class Adaptor:

    def __init__(self, name, parent, performer, sender=None):
        self.name = name
        self.parent = parent
        self.sender = sender
        self.performer = performer
        if not hasattr(self.performer, 'adaptor'):
            txt = f'The performer "{name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.performer.adaptor = self
        self.queue = None
        self.is_running = False
        self.ticker_admin = None
        self.observers = {}
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.cumulative_period = 10
        logging.info(f'{self.get_alias(self)} is created')

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
                logging.exception(ex)
        self.is_running = True
        await self.is_running_notification()
        while True:
            try:
                msg = await self.queue.get()
                command = msg.get('command')
                if command not in self.not_log_commands:
                    if command in self.cumulative_commands.keys():
                        self.cumulative_commands[command]['received'] += 1
                    else:
                        logging.debug(log_util.async_received_log(self.performer, msg))
                if command in ADAPTOR_COMMANDS:
                    if not await self.handle(msg):
                        logging.warning(self.get_alias() + ' The message is not handled: ' + str(msg))
                    if params.instance.get('exit'):
                        break
                    continue
                if await self.performer.handle(msg):
                    await self.notify(msg)
                else:
                    logging.warning(self.get_alias() + ' The message is not handled: ' + str(msg))
            except asyncio.exceptions.CancelledError:
                break
            except BaseException as ex:
                logging.exception(ex)
        if hasattr(self.performer, 'exit'):
            try:
                await self.performer.exit()
            except Exception as ex:
                logging.exception(ex)

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
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'exit':
            return await self.exit(msg)
        elif command == 'cumulative_tick':
            self.cumulative_tick()
        elif command == 'cumulative_commands_set':
            await self.cumulative_commands_set(body.get('commands'), sender)
        elif command == 'cumulative_commands_remove':
            await self.cumulative_commands_remove(body.get('commands'), sender)
        elif command == 'not_log_commands_set':
            await self.not_log_commands_set(body.get('commands'), sender)
        elif command == 'not_log_commands_remove':
            await self.not_log_commands_remove(body.get('commands'), sender)
        elif command == 'subscribe':
            self.subscribe(body.get('command'), msg.get('sender'))
        elif command == 'unsubscribe':
            self.unsubscribe(body.get('command'), msg.get('sender'))
        else:
            return False
        return True

    async def exit(self, msg):
        if isinstance(self.performer, HeadPrimeAdmin):
            params.instance['exit'] = True
        else:
            msg['recipient'] = self.get_head_addr()
            await self.send(msg)
        return True

    def cumulative_tick(self):
        for command in self.cumulative_commands.keys():
            count = self.cumulative_commands[command]['received']
            logging.info(f'{self.get_alias(self)} received {count} "{command}" messages')
            count = self.cumulative_commands[command]['local_sent']
            if count > 0:
                logging.info(f'{self.get_alias(self)} sent {count} "{command}" messages')
            count = self.cumulative_commands[command]['remote_sent']
            if count > 0:
                logging.info(f'{self.get_alias(self)} SENT {count} "{command}" MESSAGES')
            count = self.cumulative_commands[command]['local_asked']
            if count > 0:
                logging.info(f'{self.get_alias(self)} asked {count} "{command}" messages')
            count = self.cumulative_commands[command]['remote_asked']
            if count > 0:
                logging.info(f'{self.get_alias(self)} ASKED {count} "{command}" MESSAGES')
            self.cumulative_commands[command]['received'] = 0
            self.cumulative_commands[command]['local_sent'] = 0
            self.cumulative_commands[command]['remote_sent'] = 0
            self.cumulative_commands[command]['local_asked'] = 0
            self.cumulative_commands[command]['remote_asked'] = 0

    async def cumulative_commands_set(self, commands, recipient=None):
        for command in commands:
            val = {'received': 0, 'local_sent': 0, 'remote_sent': 0, 'local_asked': 0, 'remote_asked': 0}
            self.cumulative_commands[command] = val
        name = 'cumulative'
        if not self.ticker_admin or not self.ticker_admin.is_ticker_exists(name):
            self.add_ticker(self.cumulative_period, command='cumulative_tick', name=name)
        if recipient:
            await self.send(self.get_msg('set', recipient=recipient))

    async def cumulative_commands_remove(self, commands, recipient=None):
        for command in commands:
            del self.cumulative_commands[command]
        if not self.cumulative_commands:
            self.ticker_admin.remove('cumulative')
        if recipient:
            await self.send(self.get_msg('removed', recipient=recipient))

    async def not_log_commands_set(self, commands, recipient=None):
        self.not_log_commands.update(commands)
        if recipient:
            await self.send(self.get_msg('set', recipient=recipient))

    async def not_log_commands_remove(self, commands, recipient=None):
        for command in commands:
            del self.cumulative_commands[command]
        if recipient:
            await self.send(self.get_msg('removed', recipient=recipient))

    def subscribe(self, command, sender):
        res = self.observers.get(command)
        if not res:
            res = []
            self.observers[command] = res
        res.append(sender)

    def unsubscribe(self, command, sender):
        res = self.observers.get(command)
        if res:
            res.remove(sender)

    async def notify(self, msg):
        res = self.observers.get(msg.get('command'))
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
        if self.parent:
            return await self.parent.connector.ask(self, msg, timeout)
        else:
            await self.performer.connector.ask(self, msg, timeout)

    async def group_ask(self, timeout, count, get_values):
        return await self.parent.connector.group_ask(self, timeout, count, get_values)

    def add_ticker(self, period, delay=None, count=None, name=None, command=None):
        if not self.ticker_admin:
            self.ticker_admin = ticker_admin.TickerAdmin()
        if self.ticker_admin.is_ticker_exists(name):
            return name
        return self.ticker_admin.add_ticker(self.queue, period, delay, count, name, command)

    def remove_ticker(self, name):
        if not self.ticker_admin:
            return
        self.ticker_admin.remove_ticker(name)

    async def get_queue(self, addr):
        return await self.parent.connector.get_queue(addr)

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

    def get_test_param(self, param_name):
        return params.test_instance.get(param_name)

    def get_addr(self, system, node, entity):
        if self.parent:
            return self.parent.connector.get_addr(system, node, entity)
        else:
            return self.performer.connector.get_addr(system, node, entity)

    def get_head_name(self):
        return self.parent.connector.get_head_name()

    def get_head_addr(self):
        if self.parent:
            return self.parent.connector.get_head_addr()
        else:
            return self.performer.connector.get_head_addr()

    def get_prime_name(self):
        if self.parent:
            return self.parent.connector.get_prime_name()
        else:
            return self.performer.connector.get_prime_name()

    def get_prime_addr(self):
        if self.parent:
            return self.parent.connector.get_prime_addr()
        else:
            return self.performer.connector.get_prime_addr()

    def get_serializer(self):
        return serialization.Serializer()

    def makedir(self, dirpath, clear=False):
        dir_operations.makedir(dirpath, clear)

    def execute(self, cmd):
        return terminal_util.execute(cmd)

    def sync_as_async(self, sync_function, sync_args=None):
        return thread_util.sync_as_async(sync_function, sync_args)

    async def com_exe(self, coms, timeout=300):
        if isinstance(coms, str):
            coms = ([coms], timeout)
        elif isinstance(coms, list):
            coms = (coms, timeout)
        res = await self.sync_as_async(self.execute, sync_args=coms)
        res1 = res[1]
        if len(res1) > 200:
            res1 = res1[:200] + ' >>>>'
        res2 = res[2]
        if len(res2) > 200:
            res2 = res2[:200] + ' >>>>'
        if res[0] == 0:
            logging.debug(f'{coms}: ({res[0]}, {res1}, {res2})')
        else:
            raise Exception(f'{coms}: ({res[0]}, {res1}, {res2})')
        return res

    def series_next(self, name):
        return series_admin.instance.next(name)

    async def add_to_cache(self, node, names):
        await self.parent.connector.add_to_cache(node, names)

    def get_caller_info(self):
        caller_frame = inspect.currentframe().f_back
        caller_info = inspect.getframeinfo(caller_frame)
        file_name = caller_info.filename
        module_name = inspect.getmodulename(file_name)
        line_number = caller_info.lineno
        package_name = None
        module = inspect.getmodule(caller_frame)
        if module and hasattr(module, '__package__'):
            package_name = module.__package__
        return f'Package: {package_name}, Module: {module_name}, Line: {line_number}'

    def start_timer(self, timeout, queue=None, mid=None):
        if not queue:
            queue = self.queue
        timer.start(timeout, queue, mid)
