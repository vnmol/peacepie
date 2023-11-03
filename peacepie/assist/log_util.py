from peacepie import adaptor


def get_alias(obj):
    performer = obj.performer if type(obj) is adaptor.Adaptor else obj
    perf = performer
    res = None
    while True:
        if hasattr(perf, 'adaptor') and perf.adaptor and type(perf.adaptor) is adaptor.Adaptor:
            res = perf.__class__.__name__ + f' "{perf.adaptor.name}"' + (f' ({res})' if res else '')
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
    return get_alias(sender) + ' sent: ' + str(msg)


def async_ask_log(sender, msg):
    return get_alias(sender) + ' asked: ' + str(msg)


def async_received_log(sender, msg):
    return get_alias(sender) + ' received: ' + str(msg)


def sync_sent_log(sender, msg):
    return get_alias(sender) + f' SENT: {msg}'


def sync_ask_log(sender, msg):
    return get_alias(sender) + f' ASKED: {msg}'


def sync_received_log(sender, msg):
    return get_alias(sender) + f' RECEIVED: {msg}'
