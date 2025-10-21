import asyncio
import logging
import importlib
import os
import time

from peacepie import params, msg_factory
from peacepie.assist import auxiliaries, dir_opers, log_util, version

shared_folders = {'__pycache__', 'bin'}


class PackageAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.waiters = {}
        self.work_path = f'{params.instance["package_dir"]}/work/{self.parent.parent.process_name}'
        dir_opers.adjust_path(params.instance['package_dir'], self.parent.parent.process_name, shared_folders)
        logging.info(log_util.get_alias(self) + ' is created')

    async def get_class(self, class_desc, timeout):
        if not timeout:
            timeout = 120
        try:
            pack = await self.get_package(class_desc, timeout)
            if not pack:
                return None
            if class_desc.get('class'):
                return getattr(pack, class_desc.get('class'))
            else:
                return auxiliaries.get_primary_class(pack)
        except Exception as ex:
            logging.exception(ex)
        return None

    async def get_package(self, class_desc, timeout):
        requires_dist = version.parse_requires_dist(class_desc.get('requires_dist'))
        package_name = requires_dist.get('package_name')
        version_spec = requires_dist.get('version_spec')
        if not class_desc.get('class'):
            return importlib.import_module(package_name)
        is_exist = self.check_version(package_name, version_spec)
        if is_exist is not None:
            if is_exist:
                return importlib.import_module(package_name)
            else:
                return None
        if params.instance.get('developing_mode'):
            res = await self.developing_symlink(package_name, version_spec)
            if res:
                return res
        res = await self.retrieve_package(requires_dist, class_desc.get('extra-index-url'), timeout)
        return res

    def check_version(self, package_name, version_spec):
        for entry in os.listdir(self.work_path):
            entry_path = f'{self.work_path}/{entry}'
            if not (os.path.isdir(entry_path) and entry.endswith('.dist-info')):
                continue
            name, ver, _ = dir_opers.get_metadata(entry_path)
            if name == package_name:
                return version.check_version(ver, version_spec)
        return None

    async def developing_symlink(self, package_name, version_spec):
        path = f'{params.instance.get("plugin_dir")}/{package_name}'
        vers = [name for name in os.listdir(path) if version.version_from_string(name)]
        ver = version.find_max_version(vers, version_spec)
        src = f'{path}/{ver}'
        if dir_opers.is_dir_exist(f'{src}/src'):
            src = f'{src}/src/{package_name}'
        else:
            src = f'{src}/{package_name}'
        if await dir_opers.create_symlink(src, f'{self.work_path}/{package_name}'):
            self.create_package_info(package_name, ver)
            return importlib.import_module(package_name)
        return None

    def create_package_info(self, package_name, ver):
        package_info_path = f'{self.work_path}/{package_name}-{ver}.dist-info'
        dir_opers.recreatedir(package_info_path)
        with open(f'{package_info_path}/METADATA', 'w', encoding='utf-8') as f:
                 f.write(f'Name: {package_name}\n')
                 f.write(f'Version: {ver}\n')

    async def retrieve_package(self, requires_dist, url, timeout):
        queue = asyncio.Queue()
        if not url:
            url = params.instance.get('extra-index-url')
        waiter = {'requires_dist': requires_dist, 'url':url, 'timeout': timeout, 'queue': queue}
        package_name = requires_dist.get('package_name')
        waiters = self.waiters.get(package_name)
        if waiters:
            active = waiters.pop()
            waiters.append(waiter)
            waiters.sort(key=lambda x: x['timeout'])
            waiters.append(active)
        else:
            waiters = [waiter]
            self.waiters[package_name] = waiters
            asyncio.get_running_loop().create_task(self.acquire_package(package_name, waiters))
        res = await queue.get()
        return res

    async def acquire_package(self, package_name, waiters):
        start = time.time()
        while waiters:
            active = waiters[-1]
            if active.get('timeout') < time.time() - start:
                for waiter in waiters:
                    await waiter.get('queue').put(None)
                break
            res = await self.load_package(active)
            if res:
                for waiter in waiters:
                    await waiter.get('queue').put(res)
                break
            else:
                await active.get('queue').put(None)
            waiters.pop()
        del self.waiters[package_name]

    async def load_package(self, active):
        recipient = self.parent.parent.adaptor.get_head_addr()
        requires_dist = active.get('requires_dist')
        package_name = requires_dist.get('package_name')
        version_spec = requires_dist.get('version_spec')
        body = {'requires_dist': requires_dist, 'url': active.get('url')}
        msg = msg_factory.get_msg('load_package', body, recipient)
        ans = await self.parent.parent.adaptor.ask(msg, active.get('timeout'), self)
        if ans.get('command') == 'package_is_loaded':
            try:
                bundle = ans.get('body').get('bundle')
                packages = {}
                for member in bundle:
                    name, ver = member.rsplit('-', 1)
                    packages[name] = ver
                need_to_link = self.need_to_link(package_name, version_spec, packages)
                if await self.link_packages(need_to_link):
                        return importlib.import_module(package_name)
            except Exception as e:
                logging.exception(e)
        return None

    def need_to_link(self, package_name, version_spec, packages):
        is_exist = self.check_version(package_name, version_spec)
        if is_exist is not None:
            if is_exist:
                return {}
            else:
                return None
        ver = packages.get(package_name)
        if not ver:
            return None
        result = {package_name: ver}
        dependencies = self.get_dependencies(package_name, ver)
        for dependency in dependencies:
            res = self.need_to_link(dependency.get('package_name'), dependency.get('version_spec'), packages)
            if res is None:
                return None
            else:
                result.update(res)
        return result

    def get_dependencies(self, package_name, package_ver):
        path = f'{params.instance.get("source_path")}/{package_name}-{package_ver}'
        for entry in os.listdir(path):
            entry_path = f'{path}/{entry}'
            if not (os.path.isdir(entry_path) and entry.endswith('.dist-info')):
                continue
            _, _, dependencies = dir_opers.get_metadata(entry_path)
            return dependencies
        return []

    async def link_packages(self, packages):
        if packages is None:
            return False
        for package_name in packages:
            src_path = f'{params.instance.get("source_path")}/{package_name}-{packages.get(package_name)}'
            dst_path = f'{self.work_path}'
            await dir_opers.link_package(f'{src_path}', f'{dst_path}', shared_folders)
        return True

