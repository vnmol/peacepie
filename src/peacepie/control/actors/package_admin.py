import asyncio
import inspect
import logging
import importlib
import os
import re
import time

from peacepie import params, msg_factory
from peacepie.assist import dir_operations, log_util, version


class PackageAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.waiters = {}
        self.source_path = params.instance.get('source_path')
        self.work_path = f'{params.instance["package_dir"]}/work/{self.parent.parent.process_name}'
        dir_operations.recreatedir(self.work_path)
        dir_operations.adjust_path(params.instance['package_dir'], self.parent.parent.process_name)
        logging.info(log_util.get_alias(self) + ' is created')

    async def get_class(self, class_desc, timeout):
        try:
            pack = await self.get_package(class_desc, timeout)
            if not pack:
                return None
            if class_desc.get('class'):
                return getattr(pack, class_desc.get('class'))
            else:
                return get_primary_class(pack)
        except Exception as ex:
            logging.exception(ex)
        return None

    async def get_package(self, class_desc, timeout):
        requires_dist = version.parse_requires_dist(class_desc.get('requires_dist'))
        package_name = requires_dist.get('package_name')
        if not class_desc.get('class'):
            return importlib.import_module(package_name)
        elif params.instance.get('developing_mode'):
            version_spec = requires_dist.get('version_spec')
            dst = f'{self.work_path}/{package_name}'
            if dir_operations.is_symlink_exist(dst):
                if self.check_package_info(package_name, version_spec):
                    return importlib.import_module(package_name)
                else:
                    return None
            res = self.developing_symlink(package_name, version_spec, dst)
            if res:
                return res
        return await self.retrieve_package(requires_dist, class_desc.get('extra-index-url'), timeout)

    def check_package_info(self, package_name, version_spec):
        pattern = re.compile(rf'^{re.escape(package_name)}-(?P<version>\d+\.\d+\.\d+)\.dist-info$')
        for entry in os.listdir(self.work_path):
            match = pattern.match(entry)
            if match:
                res = version.check_version(match.group('version'), version_spec)
                return res
        return False

    def developing_symlink(self, package_name, version_spec, dst):
        path = f'{params.instance.get("plugin_dir")}/{package_name}'
        vers = [version.version_from_string(name) for name in os.listdir(path) if version.version_from_string(name)]
        ver = version.find_max_version(vers, version_spec)
        src = f'{path}/{version.version_to_string(ver)}/{package_name}'
        res = None
        if dir_operations.create_symlink(src, dst):
            res = importlib.import_module(package_name)
            self.create_package_info(package_name, ver)
        return res

    def create_package_info(self, package_name, ver):
        dir_operations.recreatedir(f'{self.work_path}/{package_name}-{version.version_to_string(ver)}.dist-info')


    async def retrieve_package(self, requires_dist, url, timeout):
        queue = asyncio.Queue()
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
        body = {'requires_dist': requires_dist, 'url': active.get('url')}
        msg = msg_factory.get_msg('load_package', body, recipient)
        ans = await self.parent.parent.adaptor.ask(msg, active.get('timeout'), self)
        if ans.get('command') == 'package_is_loaded':
            try:
                res = self.link_package(requires_dist, ans.get('body').get('ver'))
                return res
            except Exception as e:
                logging.exception(e)
        return None

    def link_package(self, requires_dist, ver):
        package_name = requires_dist.get('package_name')
        dst = f'{self.work_path}/{package_name}'
        if dir_operations.is_symlink_exist(dst):
            if self.check_package_info(package_name, requires_dist.get('version_spec')):
                return importlib.import_module(package_name)
            else:
                return None
        source_path = params.instance.get('source_path')
        with open(f'{source_path}/{package_name}-{ver}.dist-info/BUNDLE', 'r', encoding='utf-8') as file:
            entries = [entry.strip() for entry in file.readlines()]
        for entry in entries:
            pack_name, pack_ver = entry.rsplit('-', 1)
            dir_operations.create_symlink(f'{source_path}/{entry}', f'{self.work_path}/{pack_name}')
            pack_info = f'{pack_name.removesuffix(".py")}-{pack_ver}.dist-info'
            dir_operations.create_symlink(f'{source_path}/{pack_info}', f'{self.work_path}/{pack_info}')
        return importlib.import_module(package_name)


def get_primary_class(module):
    classes = inspect.getmembers(module, inspect.isclass)
    if classes:
        primary_class_name, primary_class = classes[0]
        return primary_class
    else:
        return None
