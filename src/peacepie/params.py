import logging
import os
import socket

from peacepie.assist import dir_operations

instance = None
test_instance = None


def init_params(path, test_params):
    global instance
    global test_instance
    test_instance = test_params
    res = {}
    params = []
    try:
        with open(path) as f:
            pass
    except (FileNotFoundError, TypeError):
        path = None
    if not path:
        path = deploy_environment()
    try:
        with open(path) as f:
            params = [line.strip().split('#')[0] for line in f.readlines()]
    except BaseException as bex:
        print(bex)
    for param in params:
        if params == '':
            continue
        lst = param.strip().split('=', 1)
        if len(lst) == 2 and not lst[0].strip() == '' and not lst[1].strip() == '':
            name = lst[0].strip()
            value = lst[1].strip()
            if name == 'developing_mode' or name == 'separate_log_per_process':
                value = value.lower() == 'true'
            elif name == 'inter_port':
                value = int(value)
            elif name == 'intra_port':
                value = int(value)
            elif name == 'package_dir':
                value = normalize(value)
            elif name == 'plugin_dir':
                value = normalize(value)
            elif name == 'log_dir':
                value = normalize(value)
            res[name] = value
    res['ip'] = get_ip()
    instance = res


def normalize(value):
    return value[:-1] if value.endswith('/') else value


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('8.8.8.8', 1))
        res = s.getsockname()[0]
    except OSError:
        res = '127.0.0.1'
    finally:
        s.close()
    return res

def deploy_environment():
    src = f'{os.path.dirname(__file__)}/resources/config/'
    dst = f'{os.getcwd()}/config/'
    dir_operations.rem_dir(dst)
    dir_operations.copy_dir(src, dst)
    return dst + 'peacepie.cfg'
