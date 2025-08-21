import asyncio
import re

from peacepie import adaptor


def get_alias(obj):
    performer = obj.performer if isinstance(obj, adaptor.Adaptor) else obj
    perf = performer
    res = None
    while True:
        if hasattr(perf, 'adaptor') and perf.adaptor and type(perf.adaptor) is adaptor.Adaptor:
            res = f'{perf.__class__.__name__} "{perf.adaptor.name}"' + (f' ({res})' if res else '')
            break
        if hasattr(perf, 'parent') and perf.parent is not None:
            if hasattr(perf, 'name'):
                res = f'"{perf.name}"' + (f'({res})' if res else '')
            else:
                res = perf.__class__.__name__ + (f'({res})' if res else '')
            perf = perf.parent
        else:
            name = perf.__class__.__name__
            if hasattr(perf, 'name'):
                name += f' "{perf.name}"'
            res = f'{name}' + (f' ({res})' if res else '')
            break
    return res


def async_sent_log(sender, msg):
    return get_alias(sender) + f' sent: {msg_format(msg)}'


def async_ask_log(sender, msg):
    return get_alias(sender) + f' asked: {msg_format(msg)}'


def async_received_log(sender, msg):
    return get_alias(sender) + f' received: {msg_format(msg)}'


def sync_sent_log(sender, msg):
    return get_alias(sender) + f' SENT: {msg_format(msg)}'


def sync_ask_log(sender, msg):
    return get_alias(sender) + f' ASKED: {msg_format(msg)}'


def sync_received_log(sender, msg):
    return get_alias(sender) + f' RECEIVED: {msg_format(msg)}'


def msg_format(msg):
    res = "{'mid': '" + msg.get('mid') + "', 'command': '" + str(msg.get('command'))
    res += "', 'body': " + body_format(msg.get('body')) + ", 'recipient': " + addr_format(msg.get('recipient'))
    res += ", 'sender': " + addr_format(msg.get('sender')) + ", 'timeout': " + str(msg.get('timeout'))
    res += "}"
    return res


pattern = r"'password':\s*(['\"])(.*?)(\1)"


def body_format(body):
    res = str(body)
    return re.sub(pattern, r"'password': '******'", res)


def addr_format(addr):
    if isinstance(addr, str):
        return f"'{addr}'"
    elif isinstance(addr, asyncio.Queue):
        return f'{addr.__class__.__name__}({id(addr)})'
    else:
        return str(addr)
