import socket

instance = None

EXTRA_INDEX_URL = 'extra-index-url'

DEFAULT_PARAMS = {
    'log_config': './config/logs.cfg', 'system_name': 'system', 'host_name': 'prime', 'process_name': 'main',
    'intra_role': 'master', 'intra_host': 'localhost', 'intra_port': 5998, 'inter_port': 5999,
    'package_dir': './packages', EXTRA_INDEX_URL: 'https://test.pypi.org/simple/',
    'starter': '{"class_desc": {"package_name":"peacepie_example", "class":"HelloWorld"}, "name":"starter"}',
    'start_command': '{"command":"start"}'
}


def init_params(prms):
    global instance
    if prms and EXTRA_INDEX_URL not in prms.keys():
        prms[EXTRA_INDEX_URL] = None
    for key in DEFAULT_PARAMS.keys():
        if key not in prms.keys():
            prms[key] = DEFAULT_PARAMS[key]
    path = prms['package_dir']
    if path.endswith('/'):
        path = path[:-1]
        prms['package_dir'] = path
    prms['ip'] = get_ip()
    instance = prms


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


