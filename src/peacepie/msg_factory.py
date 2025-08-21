import logging

from peacepie import params
from peacepie.assist import log_util

mid_gen = 0

instance = None


def init_msg_factory(host_name, process_name, name, queue):
    global instance
    instance = MsgFactory(host_name, process_name, name, queue)


def get_msg(command, body=None, recipient=None, sender=None, timeout=None, group_mid=None):
    return instance.get_msg(command, body, recipient, sender, timeout, group_mid)


def get_group_mid():
    global mid_gen
    res = mid_gen
    mid_gen += 1
    return res


class MsgFactory:

    def __init__(self, host_name, process_name, name, queue):
        self.logger = logging.getLogger()
        self.name = f'{host_name}.{process_name}.{name}'
        self.system_name = params.instance['system_name']
        self.host_name = host_name
        self.process_name = process_name
        self.queue = queue
        self.logger.info(f'{log_util.get_alias(self)} is created')

    def get_queue(self):
        return self.queue

    def get_mid(self, group_mid):
        global mid_gen
        res = f'{self.system_name}.{self.host_name}.{self.process_name}.{mid_gen}'
        if group_mid:
            res += f'({group_mid})'
        mid_gen += 1
        return res

    def get_msg(self, command, body=None, recipient=None, sender=None, timeout=None, group_mid=None):
        res = {'mid': self.get_mid(group_mid), 'command': command, 'body': body, 'recipient': recipient,
               'sender': sender, 'timeout': timeout}
        return res
