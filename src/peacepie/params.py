import logging
import multiprocessing
import re
import sys
import socket
from importlib import resources
from pathlib import Path

from peacepie.assist import dir_opers, log_util, version
from peacepie.assist.auxiliaries import is_testing


instance = None
test_instance = None


def init_params(path, test_params):
    global instance
    global test_instance
    test_instance = test_params
    params = []
    try:
        with open(path) as f:
            params = [line.strip().split('#')[0] for line in f.readlines()]
    except BaseException as bex:
        print(bex)
    res = {}
    for param in params:
        if params == '':
            continue
        lst = param.strip().split('=', 1)
        if len(lst) == 2 and not lst[0].strip() == '' and not lst[1].strip() == '':
            name = lst[0].strip()
            value = lst[1].strip()
            if value.lower() == 'true' or value.lower() == 'false':
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
    res['source_path'] = f'{res.get("package_dir")}/source'
    res['ip'] = get_ip()
    ver = version.version_from_string(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
    ver[version.MINOR_LEVEL] = 12
    res['python_version'] = ver
    if res.get('process_name') is None:
        res['process_name'] = multiprocessing.current_process().name
    res['peacepie_version'] = get_version()
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


'''
def deploy_environment():
    if is_testing():
        return None
    src = f'{os.path.dirname(__file__)}/resources/config/'
    dst = f'{os.getcwd()}/config/'
    dir_opers.rem_dir(dst)
    dir_opers.copy_dir(src, dst)
    return dst + 'peacepie.cfg'
'''


def get_version():
    try:
        base_path = Path(__file__).resolve().parent.parent
        pyproject_path = base_path / 'pyproject.toml'
        if pyproject_path.exists():
            return read_version_from_pyproject(pyproject_path)
        dist_info_dirs = list(base_path.glob('peacepie*.dist-info'))
        if dist_info_dirs:
            metadata_path = dist_info_dirs[0] / 'METADATA'
            if metadata_path.exists():
                return read_version_from_metadata(metadata_path)
    except Exception as e:
        logging.exception(e)
    return 'unknown'


def read_version_from_pyproject(pyproject_path):
    with open(pyproject_path, 'r', encoding='utf-8') as f:
        content = f.read()
    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    if version_match:
        return version_match.group(1)

    raise ValueError('Version not found in "pyproject.toml"')


def read_version_from_metadata(metadata_path):
    with open(metadata_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.lower().startswith('version:'):
                return line.split(':', 1)[1].strip()
    raise ValueError('Version not found in "METADATA"')


def get_param(name, default=None):
    res = instance.get(name)
    if res is None:
        res = default
    return res


def create_params():
    try:
        return _create_params()
    except Exception as e:
        print(e)


def _create_params():
    source_folder = resources.files('peacepie.resources.config')
    if not source_folder.is_dir():
        return None
    dest_folder = Path.cwd() / 'config'
    dest_folder.mkdir(parents=True, exist_ok=True)

    def copy_recursive(src, dest):
        for item in src.iterdir():
            dest_path = dest / item.name
            if item.is_file():
                if not dest_path.exists():
                    dest_path.write_bytes(item.read_bytes())
            elif item.is_dir():
                if not dest_path.exists():
                    dest_path.mkdir(parents=True, exist_ok=True)
                copy_recursive(item, dest_path)

    copy_recursive(source_folder, dest_folder)
    return str(dest_folder / 'peacepie.cfg')