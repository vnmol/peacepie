import asyncio
import logging

from peacepie import msg_factory, params
from peacepie.assist import log_util, timer

EXCLUSION_COMMANDS = {'create_process'}


class Connector:

    def __init__(self, parent):
        self.parent = parent
        logging.info(log_util.get_alias(self) + ' is created')

    async def clarify_recipient(self, recipient, is_control=False):
        if recipient is None:
            if is_control:
                return self.parent.adaptor.control_queue
            else:
                return self.parent.adaptor.queue
        if type(recipient) is dict:
            system_name = recipient.get('system')
            if system_name and system_name != params.instance.get('system_name'):
                head = self.parent.adaptor.get_head_name()
                if head == self.parent.adaptor.name:
                    return self.parent.interlink.queue
                else:
                    return await self.parent.intralink.get_intra_queue(head)
            if recipient.get('node') == self.parent.adaptor.name:
                if recipient.get('entity'):
                    res = self.parent.actor_admin.get_actor_queue(recipient.get('entity'), is_control)
                    if res:
                        return res
                    recipient = recipient.get('entity')
                else:
                    return self.parent.adaptor.queue
            else:
                return await self.parent.intralink.get_intra_queue(recipient['node'])
        if type(recipient) is str:
            if recipient == self.parent.adaptor.name:
                if is_control:
                    return self.parent.adaptor.control_queue
                else:
                    return self.parent.adaptor.queue
            elif recipient.startswith('_'):
                return self.parent.asks.get(recipient)
            else:
                res = self.parent.cache.get(recipient)
                if not res:
                    res = self.parent.actor_admin.get_actor_queue(recipient, is_control)
                if not res:
                    res = await self.parent.intralink.get_intra_queue(recipient)
                return res
        else:
            return recipient

    async def send(self, sender, msg):
        recipient = msg.get('recipient')
        res = await self.clarify_recipient(recipient, msg.get('is_control'))
        if not res:
            self.find_and_send(sender, msg)
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

    async def ask(self, questioner, msg, timeout=1):
        recipient = msg.get('recipient')
        res = await self.clarify_recipient(recipient, msg.get('is_control'))
        if not res:
            res = await self.find(questioner, recipient)
            if not res:
                return
        msg['timeout'] = timeout
        queue = asyncio.Queue()
        entity = f'_{self.parent.ask_index}'
        self.parent.ask_index += 1
        msg['sender'] = {'node': self.parent.adaptor.name, 'entity': entity}
        self.parent.asks[entity] = queue
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
        del self.parent.asks[entity]
        return ans

    async def group_ask(self, questioner, timeout, count, get_values):
        entity = f'_{self.parent.ask_index}'
        self.parent.ask_index += 1
        queue = asyncio.Queue()
        self.parent.asks[entity] = queue
        sender = {'node': self.parent.adaptor.name, 'entity': entity}
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
                del self.parent.asks[entity]
                return ans
            else:
                await self.parent.try_put_to_cache(ans)
                self.answer_on_ask_log(questioner, ans)
        del self.parent.asks[entity]
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

    def find_and_send(self, sender, msg):
        asyncio.get_running_loop().create_task(self._find_and_send(sender, msg))

    async def _find_and_send(self, sender, msg):
        recipient = await self.find(sender, msg['recipient'])
        if not recipient:
            return
        await recipient.put(msg)
        logging.debug(log_util.sync_sent_log(sender, msg))

    async def find(self, sender, name):
        res = None
        msg = msg_factory.get_msg('seek_actor', {'name': name}, self.parent.adaptor.get_head_addr())
        ans = await self.ask(sender, msg, 2)
        if ans['command'] == 'actor_found':
            res = await self.parent.intralink.get_intra_queue(ans['body']['node'])
            if res:
                self.parent.cache[name] = res
            else:
                logging.warning(f'The actor "{name}" is not found')
        return res
