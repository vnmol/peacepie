import asyncio
import inspect
import logging

from peacepie.assist import log_util, json_util, serialization, dir_operations, terminal_util, thread_util, timer
from peacepie import msg_factory, params
from peacepie.control import ticker_admin, series_admin
from peacepie.control.head_prime_admin import HeadPrimeAdmin

ADAPTOR_COMMANDS = {'exit', 'subscribe', 'unsubscribe', 'not_log_commands_set', 'not_log_commands_remove',
                    'cumulative_commands_set', 'cumulative_commands_remove', 'cumulative_tick',
                    'set_availability', 'update_running', 'empty'}


class Adaptor:

    def __init__(self, class_desc, name, parent, performer, sender=None):
        self.name = name
        self.parent = parent
        self.admin = parent if parent else performer
        self.sender = sender
        self.class_desc = class_desc
        self.is_enabled = True
        self.performer = performer
        if not hasattr(self.performer, 'adaptor'):
            txt = f'The performer "{name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.performer.adaptor = self
        self.control_queue = None
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
        self.control_queue = asyncio.Queue()
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
                if self.control_queue.empty() and self.is_enabled and self.is_running:
                    msg = await self.queue.get()
                else:
                    msg = await self.control_queue.get()
                if not msg:
                    continue
                command = msg.get('command')
                if command not in self.not_log_commands:
                    if command in self.cumulative_commands.keys():
                        self.cumulative_commands[command]['received'] += 1
                    else:
                        logging.debug(log_util.async_received_log(self.performer, msg))
                if command in ADAPTOR_COMMANDS:
                    if not await self.handle(msg):
                        logging.warning(self.get_alias() + ' The message is not handled: ' + str(msg))
                        if msg.get('sender'):
                            await self.send(self.get_msg('is_not_handled', recipient=msg.get('sender')))
                    if params.instance.get('exit'):
                        break
                    continue
                if await self.performer.handle(msg):
                    await self.notify(msg)
                else:
                    logging.warning(self.get_alias() + ' The message is not handled: ' + str(msg))
                    if msg.get('sender'):
                        await self.send(self.get_msg('is_not_handled', recipient=msg.get('sender')))
            except asyncio.exceptions.CancelledError:
                break
            except BaseException as ex:
                logging.exception(ex)
        if hasattr(self.performer, 'exit'):
            try:
                await self.performer.exit()
            except Exception as ex:
                print(ex)
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
            self.subscribe(body.get('command'), sender)
        elif command == 'unsubscribe':
            self.unsubscribe(body.get('command'), sender)
        elif command == 'set_availability':
            await self.set_availability(body.get('value'), sender)
        elif command == 'update_running':
            await self.update_running(body.get('value'), sender)
        elif command == 'empty':
            pass
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

    async def set_availability(self, value, recipient):
        self.is_enabled = value
        if recipient:
            await self.send(self.get_msg('availability_is_set', recipient=recipient))

    async def update_running(self, value, recipient):
        self.is_running = value
        if recipient:
            await self.send(self.get_msg('running_flag_updated', recipient=recipient))

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

    def get_control_msg(self, command, body=None, recipient=None, sender=None):
        return msg_factory.get_control_msg(command, body, recipient, sender)

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
        res = None
        if isinstance(addr, str):
            res = self.parent.actor_admin.get_actor_queue(addr)
        return res

    def get_param(self, param_name):
        return params.instance.get(param_name)

    def get_test_param(self, param_name):
        return params.test_instance.get(param_name)

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

    def get_head_name(self):
        if self.parent:
            if self.parent.intralink.head:
                return self.parent.intralink.head
            else:
                return self.parent.adaptor.name
        else:
            if self.performer.intralink.head:
                return self.performer.intralink.head
            else:
                return self.name

    def get_prime_name(self):
        if self.parent:
            if self.parent.lord:
                return self.parent.lord
            else:
                return self.parent.adaptor.name
        else:
            return self.name

    def get_addr(self, system, node, entity):
        if system:
            return {'system': system, 'node': node, 'entity': entity}
        else:
            return {'node': node, 'entity': entity}

    def add_system(self, addr, system_name):
        return self.get_addr(system_name, addr['node'], addr['entity'])

    def get_head_addr(self):
        return self.get_addr(None, self.get_head_name(), None)

    def get_prime_addr(self):
        return self.get_addr(None, self.get_prime_name(), None)

    def get_self_addr(self):
        if self.parent:
            return self.get_addr(None, self.parent.adaptor.name, self.name)
        else:
            return self.get_addr(None, self.name, None)

    def get_node(self):
        if self.parent:
            return self.parent.adaptor.name
        else:
            return self.name

    async def clarify_recipient(self, recipient, is_control=False):
        if recipient is None:
            if is_control:
                return self.admin.adaptor.control_queue
            else:
                return self.admin.adaptor.queue
        if type(recipient) is dict:
            system_name = recipient.get('system')
            if system_name and system_name != params.instance.get('system_name'):
                head = self.get_head_name()
                if head == self.admin.adaptor.name:
                    return self.admin.interlink.queue
                else:
                    return await self.admin.intralink.get_intra_queue(head)
            if recipient.get('node') == self.admin.adaptor.name:
                if recipient.get('entity'):
                    res = self.admin.actor_admin.get_actor_queue(recipient.get('entity'), is_control)
                    if res:
                        return res
                    recipient = recipient.get('entity')
                else:
                    return self.admin.adaptor.queue
            else:
                return await self.admin.intralink.get_intra_queue(recipient['node'])
        if type(recipient) is str:
            if recipient == self.admin.adaptor.name:
                if is_control:
                    return self.admin.adaptor.control_queue
                else:
                    return self.admin.adaptor.queue
            elif recipient.startswith('_'):
                return self.admin.asks.get(recipient)
            else:
                res = self.admin.cache.get(recipient)
                if not res:
                    res = self.admin.actor_admin.get_actor_queue(recipient, is_control)
                if not res:
                    res = await self.admin.intralink.get_intra_queue(recipient)
                return res
        else:
            return recipient

    async def send(self, msg, sender=None):
        if not sender:
            sender = self
        recipient = msg.get('recipient')
        res = await self.clarify_recipient(recipient, msg.get('is_control'))
        if not res:
            res = await self.find(sender, recipient)
            if not res:
                return
        is_local = isinstance(res, asyncio.Queue)
        if not (is_local or isinstance(recipient, str) or isinstance(recipient, dict)):
            msg['recipient'] = None
        await res.put(msg)
        self.send_log(sender, is_local, msg)

    def send_log(self, sender, is_local, msg):
        command = msg.get('command')
        if command in sender.not_log_commands:
            return
        if command in sender.cumulative_commands.keys():
            sender.cumulative_commands[command]['local_sent' if is_local else 'remote_sent'] += 1
        elif is_local:
            logging.debug(log_util.async_sent_log(sender, msg))
        else:
            logging.debug(log_util.sync_sent_log(sender, msg))

    async def ask(self, msg, timeout=1, questioner=None):
        if not questioner:
            questioner = self
        recipient = msg.get('recipient')
        res = await self.clarify_recipient(recipient, msg.get('is_control'))
        if not res:
            print(recipient)
            res = await self.find(questioner, recipient)
            if not res:
                return
        msg['timeout'] = timeout
        queue = asyncio.Queue()
        entity = f'_{self.admin.ask_index}'
        self.admin.ask_index += 1
        msg['sender'] = {'node': self.admin.adaptor.name, 'entity': entity}
        self.admin.asks[entity] = queue
        if not (isinstance(recipient, str) or isinstance(recipient, dict)):
            msg['recipient'] = None
        await res.put(msg)
        self.ask_log(questioner, isinstance(res, asyncio.Queue), msg)
        timer.start(timeout, queue, msg['mid'])
        ans = await queue.get()
        if ans.get('command') == 'timer':
            logging.warning(log_util.async_received_log(questioner, ans))
        else:
            self.answer_on_ask_log(questioner, ans)
        del self.admin.asks[entity]
        return ans

    async def group_ask(self, timeout, count, get_values, questioner=None):
        if not questioner:
            questioner = self
        entity = f'_{self.admin.ask_index}'
        self.admin.ask_index += 1
        queue = asyncio.Queue()
        self.admin.asks[entity] = queue
        sender = {'node': self.admin.adaptor.name, 'entity': entity}
        waiting_count = count
        group_mid = msg_factory.get_group_mid()
        timer.start(timeout, queue, group_mid)
        for index in range(count):
            values = get_values(index)
            recipient = values.get('recipient')
            res = await self.clarify_recipient(recipient)
            if not res:
                res = await self.find(questioner, recipient)
                if not res:
                    waiting_count -= 1
                    continue
            recipient = recipient if isinstance(recipient, str) or isinstance(recipient, dict) else None
            command = values.get('command')
            body = values.get('body')
            msg = msg_factory.get_msg(command, body, recipient=recipient, sender=sender, timeout=timeout,
                                      group_mid=group_mid)
            await res.put(msg)
            self.ask_log(questioner, isinstance(res, asyncio.Queue), msg)
        while waiting_count > 0:
            ans = await queue.get()
            waiting_count -= 1
            if ans.get('command') == 'timer':
                del self.admin.asks[entity]
                return ans
            else:
                await self.admin.try_put_to_cache(ans)
                self.answer_on_ask_log(questioner, ans)
        del self.admin.asks[entity]
        return msg_factory.get_msg('group_ask_completed')

    def ask_log(self, questioner, is_local, msg):
        command = msg.get('command')
        if command in questioner.not_log_commands:
            return
        if command in questioner.cumulative_commands.keys():
            questioner.cumulative_commands[command]['local_asked' if is_local else 'remote_asked'] += 1
        elif is_local:
            logging.debug(log_util.async_ask_log(questioner, msg))
        else:
            logging.debug(log_util.sync_ask_log(questioner, msg))

    def answer_on_ask_log(self, questioner, msg):
        command = msg.get('command')
        if command in questioner.not_log_commands:
            return
        if command in questioner.cumulative_commands.keys():
            questioner.cumulative_commands[command]['received'] += 1
        else:
            logging.debug(log_util.async_received_log(questioner, msg))

    async def find(self, sender, name):
        res = None
        msg = msg_factory.get_msg('seek_actor', {'name': name}, self.parent.adaptor.get_head_addr())
        ans = await self.ask(msg, 2, sender)
        if ans['command'] == 'actor_found':
            res = await self.admin.intralink.get_intra_queue(ans['body']['node'])
            if res:
                self.admin.cache[name] = res
            else:
                logging.warning(f'The actor "{name}" is not found')
        return res

    async def add_to_cache(self, node, names):
        await self.admin.add_to_cache(node, names)
