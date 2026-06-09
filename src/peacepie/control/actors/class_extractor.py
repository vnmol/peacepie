import importlib
import importlib.metadata
import logging
import os
from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import Version

from peacepie import msg_factory, params
from peacepie.assist import auxiliaries, dir_opers, exceptions, version
from peacepie.control.admin import Admin


shared_folders = {'__pycache__', 'bin'}


async def get_class(adaptor, class_desc, timeout=4, questioner=None):
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
        res = await load_and_get(adaptor, class_desc, timeout, questioner)
        return res
    except Exception as e:
        logging.exception(e)
    return None


def obtain_class(class_desc):
    requirement = Requirement(class_desc.get('requires_dist'))
    package_name = requirement.name
    if not class_desc.get('class'):
        pack = importlib.import_module(package_name)
        return auxiliaries.get_primary_class(pack)
    ver = importlib.metadata.version(package_name)
    if ver not in requirement.specifier:
        raise exceptions.VersionError
    pack = importlib.import_module(package_name)
    return getattr(pack, class_desc.get('class'))


async def load_and_get(adaptor, class_desc, timeout, questioner=None):
    requires_dist = class_desc.get('requires_dist')
    requirement = Requirement(requires_dist)
    is_admin = isinstance(adaptor.performer, Admin)
    work_path = adaptor.performer.actor_admin.work_path if is_admin else adaptor.parent.actor_admin.work_path
    if params.instance.get('developing_mode'):
        res = developing_symlink(work_path, requirement, class_desc.get('class'))
        if res:
            return res
    body = {'requires_dist': requires_dist, 'index-url': class_desc.get('index-url')}
    recipient = adaptor.get_head_addr()
    query = msg_factory.get_msg('load_package', body, recipient, timeout=timeout)
    ans = await adaptor.ask(query, questioner=questioner)
    if ans.get('command') != 'package_is_loaded':
        return None
    source_path = params.instance.get('source_path')
    package_version = ans.get('body').get('package_version')
    packages = get_link_list(source_path, work_path, requirement, package_version, None)
    if link_packages(source_path, work_path, packages):
        return obtain_class(class_desc)
    return None


def developing_symlink(work_path, requirement, class_name):
    package_name = requirement.name.replace('-', '_').lower()
    path = f'{params.instance.get("plugin_dir")}/{package_name}'
    ver = None
    for name in os.listdir(path):
        v = Version(name)
        if not ver or v > ver:
            ver = v
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


def get_link_list(source_path, work_path, requirement, package_version, extra):
    package_name = requirement.name.replace('-', '_').lower()
    if extra:
        package_name += f'[{extra}]'
    in_work = is_in_work(work_path, package_name, requirement.specifier)
    if in_work is None:
        return None
    if in_work:
        return set()
    result = {f'{package_name}-{package_version}'}
    if extra is None and requirement.extras:
        for ext in requirement.extras:
            res = get_link_list(source_path, work_path, requirement, package_version, ext)
            if res is None:
                return None
            result = result.union(res)
    for req, ver in get_dependencies(get_package_info_path(source_path, package_name, package_version), extra):
        if req is None:
            return None
        res = get_link_list(source_path, work_path, req, ver, None)
        if res is None:
            return None
        result = result.union(res)
    return result


def get_package_info_path(source_path, package_name, package_version):
    name = f'{package_name}-{package_version}'
    res = Path(source_path) / name / f'{name}.dist-info'
    if not res.is_dir():
        return None
    return str(res)


def is_in_work(path, package_name, specifier):
    for item in Path(path).iterdir():
        if item.is_dir() and item.name.startswith(package_name) and item.name.endswith('.dist-info'):
            _, ver = str(item)[:-len('.dist-info')].split('-')
            if Version(ver) in specifier:
                return True
            else:
                return None
    return False


def get_dependencies(package_info_path, extra):
    if package_info_path is None:
        return [(None, None)]
    bundle = get_bundle(package_info_path)
    dist = importlib.metadata.Distribution.at(package_info_path)
    dependencies = []
    for req_str in (dist.metadata.get_all("Requires-Dist") or []):
        req = Requirement(req_str)
        ver = bundle.get(req.name.replace('-', '_').lower())
        if req.marker:
            if extra:
                if req.marker.evaluate({'extra': extra}):
                    dependencies.append((req, ver))
            elif req.marker.evaluate():
                dependencies.append((req, ver))
        else:
            dependencies.append((req, ver))
    return dependencies


def get_bundle(package_info_path):
    res = {}
    try:
        with open(f'{package_info_path}/BUNDLE', 'r', encoding='utf-8') as f:
            for line in f:
                name, ver = line.split('-')
                res[name.strip()] = ver.strip()
    except Exception as e:
        logging.exception(e)
    return res


def link_packages(source_path, work_path, packages):
        if packages is None:
            return False
        for package_name in packages:
            dir_opers.sync_link_package(f'{source_path}/{package_name}', work_path, shared_folders)
        return True


def create_package_info(work_path, package_name, package_version):
    package_info_path = Path(work_path) / f'{package_name}-{package_version}.dist-info'
    dir_opers.recreatedir(package_info_path)
    with open(f'{package_info_path}/METADATA', 'w', encoding='utf-8') as f:
        f.write(f'Name: {package_name}\n')
        f.write(f'Version: {package_version}\n')
