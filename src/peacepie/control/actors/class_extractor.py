import importlib
import importlib.metadata
import logging
import os

from peacepie import msg_factory, params
from peacepie.assist import auxiliaries, dir_opers, exceptions, version
from peacepie.control.admin import Admin


shared_folders = {'__pycache__', 'bin'}


async def get_class(adaptor, class_desc, timeout=4):
    try:
        res = obtain_class(class_desc)
        if res:
            return res
    except importlib.metadata.PackageNotFoundError:
        pass
    except Exception as e:
        logging.exception(e)
        return None
    try:
        res = await load_and_get(adaptor, class_desc, timeout)
        return res
    except Exception as e:
        logging.exception(e)
    return None


def obtain_class(class_desc):
    requires_dist = version.parse_requires_dist(class_desc.get('requires_dist'))
    package_name = requires_dist.get('package_name')
    version_spec = requires_dist.get('version_spec')
    if not class_desc.get('class'):
        pack = importlib.import_module(package_name)
        return auxiliaries.get_primary_class(pack)
    ver = importlib.metadata.version(package_name)
    if not version.check_version(ver, version_spec):
        raise exceptions.VersionError
    pack = importlib.import_module(package_name)
    return getattr(pack, class_desc.get('class'))


async def load_and_get(adaptor, class_desc, timeout):
    requires_dist = class_desc.get('requires_dist')
    parsed_requires_dist = version.parse_requires_dist(requires_dist)
    is_admin = isinstance(adaptor.performer, Admin)
    work_path = adaptor.performer.actor_admin.work_path if is_admin else adaptor.parent.actor_admin.work_path
    if params.instance.get('developing_mode'):
        package_name = parsed_requires_dist.get('package_name')
        version_spec = parsed_requires_dist.get('version_spec')
        res = developing_symlink(work_path, package_name, version_spec, class_desc.get('class'))
        if res:
            return res
    body = {'requires_dist': requires_dist, 'extra-index-url': class_desc.get('extra-index-url')}
    recipient = adaptor.get_head_addr()
    query = msg_factory.get_msg('load_package', body, recipient, timeout=timeout)
    ans = await adaptor.ask(query)
    if ans.get('command') != 'package_is_loaded':
        return None
    entry = ans.get('body').get('entry')
    source_path = params.instance.get('source_path')
    packages = get_link_list(source_path, work_path, parsed_requires_dist, entry)
    if link_packages(source_path, work_path, packages):
        return obtain_class(class_desc)
    return None


def developing_symlink(work_path, package_name, version_spec, class_name):
    path = f'{params.instance.get("plugin_dir")}/{package_name}'
    vers = [name for name in os.listdir(path) if version.version_from_string(name)]
    ver = version.find_max_version(vers, version_spec)
    source_path = f'{path}/{ver}'
    if dir_opers.is_dir_exist(f'{source_path}/src'):
        source_path = f'{source_path}/src/{package_name}'
    else:
        source_path = f'{source_path}/{package_name}'
    if dir_opers.sync_create_symlink(source_path, f'{work_path}/{package_name}'):
        create_package_info(work_path, package_name, ver)
        pack = importlib.import_module(package_name)
        return getattr(pack, class_name)
    return None


def get_link_list(source_path, work_path, requires_dist, entry):
    package_name = requires_dist.get('package_name')
    version_spec = requires_dist.get('version_spec')
    is_in_work = find_entry(work_path, package_name, version_spec)
    if is_in_work:
        return set()
    elif is_in_work is None:
        return None
    path = dir_opers.get_package_entry(source_path, entry)
    dependencies = dir_opers.get_metadata_ext(path)
    result = {entry}
    for require, pack in dependencies:
        res = get_link_list(source_path, work_path, require, pack)
        if res is None:
            return None
        result = result.union(res)
    return result


def find_entry(path, package_name, version_spec):
    for entry_path in dir_opers.get_work_package_entries(path):
        name, v, _ = dir_opers.get_metadata(entry_path)
        if name.lower().replace('-', '_') == package_name.lower().replace('-', '_'):
            if version.check_version(v, version_spec):
                return True
            else:
                pack_desc = f'Version {v} of package "{package_name}" in "{path}"'
                logging.warning(f'{pack_desc} does not meet the requirements "{version_spec}".')
                return None
    return False


def link_packages(source_path, work_path, packages):
        if packages is None:
            return False
        for package_name in packages:
            dir_opers.sync_link_package(f'{source_path}/{package_name}', work_path, shared_folders)
        return True


def create_package_info(work_path, package_name, ver):
    package_info_path = f'{work_path}/{package_name}-{ver}.dist-info'
    dir_opers.recreatedir(package_info_path)
    with open(f'{package_info_path}/METADATA', 'w', encoding='utf-8') as f:
        f.write(f'Name: {package_name}\n')
        f.write(f'Version: {ver}\n')
