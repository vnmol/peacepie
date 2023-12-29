import logging

from peacepie import params
from peacepie.assist import log_util

mid_gen = 0

instance = None


def init_msg_factory(host_name, process_name, name, queue):
    global instance
    instance = MsgFactory(host_name, process_name, name, queue)


def get_msg(command, body=None, recipient=None, sender=None):
    return instance.get_msg(command, body, recipient, sender)


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

    def get_mid(self):
        global mid_gen
        res = f'{self.system_name}.{self.host_name}.{self.process_name}.{mid_gen}'
        mid_gen += 1
        return res

    def get_msg(self, command, body=None, recipient=None, sender=None, timeout=None):
        res = {'mid': self.get_mid(), 'command': command, 'body': body, 'recipient': recipient, 'sender': sender,
               'timeout': timeout}
        return res


class Message:

    def __init__(self, mid, command, body=None, recipient=None, sender=None):
        self.mid = mid
        self.command = command
        self.body = body
        self.recipient = recipient
        self.sender = sender

    def __repr__(self):
        res = f'{self.__class__.__name__}({self.mid})(command={self.command}, '
        res += f'body={"bytes" if type(self.body) is bytes else self.body}, '
        res += f'recipient={get_addressee_name(self.recipient)}, sender={get_addressee_name(self.sender)})'
        return res


def get_addressee_name(addressee):
    if addressee:
        if isinstance(addressee, str) or isinstance(addressee, dict):
            return addressee
        else:
            return f'{addressee.__class__.__module__}.{addressee.__class__.__name__}({id(addressee)})'
    else:
        return None
