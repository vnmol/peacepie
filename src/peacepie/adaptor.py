import asyncio
import importlib
import importlib.util
import inspect
import logging
import os

from peacepie import msg_factory, params
from peacepie.assist import (auxiliaries, log_util, json_util, serialization, dir_opers, terminal_util,
                             thread_util, timer, version)
from peacepie.control import ticker_admin, series_admin
from peacepie.control.actors import class_extractor
from peacepie.control.admin import Admin
from peacepie.control.head_prime_admin import HeadPrimeAdmin


ADAPTOR_COMMANDS = {'quit', 'subscribe', 'unsubscribe', 'not_log_commands_set', 'not_log_commands_remove',
                    'cumulative_commands_set', 'cumulative_commands_remove', 'cumulative_tick',
                    'update_running', 'empty'}

CACHE_COMMANDS = {'actor_is_created', 'actors_are_created', 'actor_is_found', 'actor_is_not_found'}


class Adaptor:

    def __init__(self, class_desc, name, parent, performer, sender=None):
        self.name = name
        self.parent = parent
        self.admin = parent if parent else performer
        self.sender = sender
        self.class_desc = class_desc
        self.performer = performer
        if not hasattr(self.performer, 'adaptor'):
            txt = f'The performer "{name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.performer.adaptor = self
        self.msg = None
        self.pause_event = None
        self.idle_event = None
        self.is_idle = True
        self.stop_event = None
        self.queue = None
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

    def pause(self):
        if self.pause_event is None:
            self.pause_event = asyncio.Event()
        if not self.is_idle:
            self.idle_event = asyncio.Event()
        if self.queue.empty():
            self.queue.put_nowait(msg_factory.get_msg('empty'))
        logging.info(f'{self.get_alias(self)} is paused')

    def is_paused(self):
        return self.pause_event is not None

    def resume(self, is_stopping=False):
        if is_stopping and self.stop_event is None:
            self.stop_event = asyncio.Event()
        if self.pause_event is not None:
            self.pause_event.set()
        logging.info(f'{self.get_alias(self)}(is_stopping={is_stopping}) is resumed')

    def stop(self):
        if self.pause_event is not None:
            self.pause_event.set()
        if self.stop_event is None:
            self.stop_event = asyncio.Event()
        if self.queue.empty():
            self.queue.put_nowait(msg_factory.get_msg('empty'))

    async def is_idling(self, timeout):
        if self.is_idle:
            return True
        res, _ = await asyncio.wait([asyncio.create_task(self.idle_event.wait())], timeout=timeout)
        self.idle_event = None
        return res

    async def is_stopped(self, timeout):
        res, _ = await asyncio.wait([asyncio.create_task(self.stop_event.wait())], timeout=timeout)
        return res

    async def run(self):
        if self.queue is None:
            self.queue = asyncio.Queue()
            if hasattr(self.performer, 'pre_run'):
                try:
                    await self.performer.pre_run()
                except Exception as ex:
                    logging.exception(ex)
            await self.is_running_notification()
        while True:
            self.is_idle = True
            try:
                if self.idle_event is not None:
                    self.idle_event.set()
                if self.pause_event is not None:
                    await self.pause_event.wait()
                    self.pause_event = None
                if self.stop_event is not None:
                    break
                self.is_idle = False
                self.msg = await self.queue.get()
                if not self.msg:
                    continue
                command = self.msg.get('command')
                if command not in self.not_log_commands:
                    if command in self.cumulative_commands.keys():
                        self.cumulative_commands[command]['received'] += 1
                    else:
                        logging.debug(log_util.async_received_log(self.performer, self.msg))
                if command in ADAPTOR_COMMANDS:
                    if not await self.handle(self.msg):
                        logging.warning(self.get_alias() + ' The message is not handled: ' + str(self.msg))
                        if self.msg.get('sender'):
                            ans = self.get_msg('is_not_handled', {'mid': self.msg.get('mid')},
                                               recipient=self.msg.get('sender'))
                            await self.send(ans)
                    continue
                if await self.performer.handle(self.msg):
                    if command in CACHE_COMMANDS:
                        await self.add_to_cache(self.msg)
                    await self.notify(self.msg)
                else:
                    logging.warning(self.get_alias() + ' The message is not handled: ' + str(self.msg))
                    if self.msg.get('sender'):
                        ans = self.get_msg('is_not_handled', {'mid': self.msg.get('mid')},
                                           recipient=self.msg.get('sender'))
                        await self.send(ans)
            except asyncio.exceptions.CancelledError:
                pass
            except BaseException as ex:
                logging.exception(ex)
        await self.exit()
        if self.stop_event is not None:
            self.stop_event.set()
        logging.info(f'{self.get_alias(self)} is stopped')

    async def exit(self):
        if not hasattr(self.performer, 'exit'):
            return
        if isinstance(self.performer, Admin):
            await self.performer.exit()
            return
        timeout = 4
        if hasattr(self.performer, 'shield_timeout') and self.performer.shield_timeout > 0:
            timeout =self.performer.shield_timeout
            task = asyncio.shield(self.performer.exit())
        else:
            task = asyncio.create_task(self.performer.exit())
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            task.cancel()
        except Exception as e:
            logging.exception(e)

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
        if command == 'quit':
            await self.quit(msg)
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
        elif command == 'empty':
            pass
        else:
            return False
        return True

    async def quit(self, msg):
        if isinstance(self.performer, HeadPrimeAdmin):
            if msg.get('sender'):
                await self.send(self.get_msg('is_quiting', None, msg.get('sender')))
            await asyncio.sleep(0.4)
            asyncio.create_task(self.performer.quit())
        else:
            msg['recipient'] = self.get_head_addr()
            await self.send(msg)

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

    def get_msg(self, command, body=None, recipient=None, sender=None, timeout=None):
        return msg_factory.get_msg(command, body, recipient, sender, timeout)

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

    def get_param(self, param_name):
        return params.instance.get(param_name)

    def get_test_param(self, param_name):
        return params.test_instance.get(param_name)

    def get_serializer(self):
        return serialization.Serializer()

    def get_serializer_desc(self):
        return f"'{serialization.__name__}|{serialization.Serializer.__name__}'"

    def get_serializer_spec(self):
        path, module = os.path.split(inspect.getmodule(serialization).__file__)
        return {'path': path, 'module': os.path.splitext(module)[0], 'class': serialization.Serializer.__name__}

    def get_package_path(self, path_only:bool=True):
        res = None
        spec = importlib.util.find_spec(__package__)
        if spec and spec.origin:
            res = os.path.dirname(spec.origin)
            if path_only:
                res = os.path.dirname(res)
            res = f"'{res}'"
        return res

    def makedir(self, dirpath, clear=False):
        dir_opers.makedir(dirpath, clear)

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
        if res[0] == 0:
            logging.debug(f'{coms}: ({res[0]}, {self.res_squeeze(res[1])}, {self.res_squeeze(res[2])})')
        else:
            raise Exception(f'{coms}: ({res[0]}, {self.res_squeeze(res[1])}, {self.res_squeeze(res[2])})')
        return res

    async def command_execute(self, command, command_for_log, timeout=300):
        res = None
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.wait(), timeout)
            stdout, stderr = await process.communicate()
            res = (process.returncode, stdout.decode('utf-8'), stderr.decode('utf-8'))
            title = f'{self.get_alias()} executed command "{command_for_log}"'
            text = f'{title}: ({res[0]}, "{self.res_squeeze(res[1])}", "{self.res_squeeze(res[2])}")'
            if res[0] == 0:
                logging.debug(text)
            else:
                logging.warning(text)
        except Exception as e:
            logging.exception(e)
        return res

    async def sudo_command_execute(self, command, credentials_name, timeout=300):
        credentials = await self.get_credentials(credentials_name)
        username = credentials.get('username')
        password = credentials.get('password')
        com = f'echo "{password}" | su -c "echo {password} | sudo -S {command}" - {username}'
        password = '******'
        com_for_log = f'echo "{password}" | su -c "echo {password} | sudo -S {command}" - {username}'
        res = await self.command_execute(com, com_for_log, timeout)
        return res[0] == 0

    async def sudo_com_exe(self, credentials_name, command, cwd=None, timeout=300):
        credentials = await self.get_credentials(credentials_name)
        username = credentials.get('username')
        password = credentials.get('password')
        com = f'echo "{password}" | su -c "echo {password} | sudo -S {command}" - {username}'
        password = '******'
        com_for_log = f'echo "{password}" | su -c "echo {password} | sudo -S {command}" - {username}'
        res = await self.sync_as_async(terminal_util.exe, sync_args=(com, cwd, timeout))
        title = f'{self.get_alias()} executed command "{com_for_log}"'
        text = f'{title}: ({res[0]}, "{self.res_squeeze(res[1])}", "{self.res_squeeze(res[2])}")'
        if res[0] == 0:
            logging.debug(text)
        else:
            logging.warning(text)
        return res[0] == 0

    def res_squeeze(self, param):
        res = param[:200] + ' >>>>' if len(param) > 200 else param
        return res.replace("\n", "\\n")

    def series_next(self, name):
        return series_admin.instance.next(name)

    def series_set_value(self, name, value):
        series_admin.instance.set_value(name, value)

    def series_set_max_value(self, name, max_value):
        series_admin.instance.set_max_value(name, max_value)

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

    async def get_local_nodes(self, exclude_current=False):
        res = None
        if hasattr(self.admin, 'get_local_nodes'):
            res = await self.admin.get_local_nodes()
        else:
            ans = await self.ask(self.get_msg('get_local_nodes', None, self.get_head_name()))
            if ans.get('command') == 'local_nodes':
                res = ans.get('body')
        if exclude_current:
            res.remove(self.admin.adaptor.name)
        return res

    async def get_all_nodes(self):
        if hasattr(self.performer, 'get_all_nodes'):
            return self.performer.get_all_nodes()
        ans = await self.ask(self.get_msg('get_all_nodes', None, self.get_head_name()))
        if ans.get('command') == 'all_nodes':
            return ans.get('body')
        return None

    async def clarify_recipient(self, recipient):
        if recipient is None:
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
                    res = self.admin.actor_admin.get_actor_queue(recipient.get('entity'))
                    if res:
                        return res
                    recipient = recipient.get('entity')
                else:
                    return self.admin.adaptor.queue
            else:
                return await self.admin.intralink.get_intra_queue(recipient.get('node'))
        if type(recipient) is str:
            if recipient == self.admin.adaptor.name:
                return self.admin.adaptor.queue
            elif recipient.startswith('_'):
                return self.admin.asks.get(recipient)
            else:
                res = self.admin.cache.get(recipient)
                if not res:
                    res = self.admin.actor_admin.get_actor_queue(recipient)
                if not res:
                    res = await self.admin.intralink.get_intra_queue(recipient)
                return res
        else:
            return recipient

    async def send(self, msg, sender=None):
        if not sender:
            sender = self
        recipient = msg.get('recipient')
        res = await self.clarify_recipient(recipient)
        if not res:
            res = await self.find(sender, recipient)
            if not res:
                return
        is_local = isinstance(res, asyncio.Queue)
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
        res = await self.clarify_recipient(recipient)
        if not res:
            res = await self.find(questioner, recipient)
            if not res:
                return None
        to = msg.get('timeout')
        if to and to > timeout:
            timeout = to
        else:
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
        if ans.get('command') in CACHE_COMMANDS:
            await self.add_to_cache(ans)
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
            recipient = recipient if isinstance(recipient, (dict, str)) else None
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
                if ans.get('command') in CACHE_COMMANDS:
                    await self.add_to_cache(ans)
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

    async def find(self, sender, entity):
        res = None
        msg = msg_factory.get_msg('seek_actor', {'entity': entity}, self.admin.adaptor.get_head_addr())
        ans = await self.ask(msg, 2, sender)
        if ans.get('command') == 'actor_is_found':
            res = await self.admin.intralink.get_intra_queue(ans['body']['node'])
        self.admin.cache[entity] = res
        if res is None:
            logging.warning(f'The actor "{entity}" is not found')
        return res

    async def add_to_cache(self, msg):
        command = msg.get('command')
        body = msg.get('body')
        if not body:
            return
        system =body.get('system')
        if system and system != self.admin.adaptor.get_param('system_name'):
            return
        node = body.get('node')
        if not node or node == self.admin.adaptor.name:
            return
        if command == 'actors_are_created':
            names = body.get('entities')
            if not names:
                return
        else:
            name = body.get('entity')
            if not name:
                return
            names = [name]
        await self.admin.add_to_cache(node, names)

    async def get_credentials(self, credentials_name):
        body = {'credentials_name': credentials_name}
        query = self.get_msg('get_credentials', body, self.get_head_addr())
        ans = await self.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else {}
        return body

    def get_log_path(self):
        res = None
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                res = os.path.dirname(handler.baseFilename)
                break
        return res

    def get_current_time_string(self):
        return auxiliaries.get_current_time_string()

    def get_attributes(self):
        return [attr for attr in vars(self.performer)
                if not callable(getattr(self.performer, attr)) and not attr.startswith('_') and attr != 'adaptor']

    def get_params(self):
        return [{'name': attr, 'value': value} for attr, value in vars(self.performer).items()
                if not callable(getattr(self.performer, attr)) and not attr.startswith('_') and attr != 'adaptor']

    def set_params(self, params):
        names = self.get_attributes()
        for param in params:
            name = param.get('name')
            if name in names:
                setattr(self.performer, name, param.get('value'))

    def has_attr(self, attr_name, is_callable=False, is_coroutine=False):
        if not hasattr(self.performer, attr_name):
            return False
        if is_callable:
            method = getattr(self.performer, attr_name)
            if not callable(method):
                return False
            if is_coroutine:
                if not inspect.iscoroutinefunction(method):
                    return False
        return True

    async def get_class(self, class_desc):
        return await class_extractor.get_class(self, class_desc)

    def get_package_name(self):
        try:
            requires_dist = version.parse_requires_dist(self.class_desc.get('requires_dist'))
            return requires_dist.get('package_name')
        except Exception as e:
            logging.exception(e)
        return None

    def get_process_name(self):
        return self.parent.process_name

    async def is_exist(self, entity):
        if entity in self.admin.cache:
            return True
        if entity in self.admin.actor_admin.actors:
            self.admin.cache[entity] = self.admin.actor_admin.actors.get(entity).get('adaptor').queue
            return True
        else:
            await self.find(self, entity)
            return self.admin.cache.get(entity) is not None
