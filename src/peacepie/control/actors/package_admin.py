import asyncio
import importlib
import importlib.metadata
import inspect
import logging
import os
import subprocess
import sys

from peacepie import params, msg_factory
from peacepie.assist import log_util, version, dir_operations

CLASS = 'class'
PACKAGE = 'package'
PACKAGE_NAME = 'package_name'
URL = 'extra-index-url'


class PackageAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.packages = {}
        self.waiters = {}
        self.delivery_path = f'{params.instance["package_dir"]}/delivery'
        self.source_path = f'{params.instance["package_dir"]}/source'
        self.tmp_path = f'{params.instance["package_dir"]}/tmp/{self.parent.parent.process_name}'
        dir_operations.recreatedir(self.tmp_path)
        self.work_path = f'{params.instance["package_dir"]}/work/{self.parent.parent.process_name}'
        dir_operations.recreatedir(self.work_path)
        dir_operations.adjust_path(params.instance['package_dir'], self.parent.parent.process_name)
        logging.info(log_util.get_alias(self) + ' is created')

    def get_class(self, class_desc, timeout):
        res = self.get_package(class_desc, timeout)
        if isinstance(res, asyncio.Queue):
            return res
        try:
            res = getattr(res, class_desc.get(CLASS))
        except Exception as ex:
            logging.exception(ex)
            return None
        return res

    def get_package(self, class_desc, timeout):
        name = class_desc.get(PACKAGE_NAME)
        try:
            pack = importlib.import_module(name)
            if class_desc.get('internal'):
                return pack
            if pack:
                ver = version.from_string(importlib.metadata.version(name))
                if version.check_version(self, ver, class_desc.get(version.VERSION)):
                    return pack
                else:
                    return None
        except ModuleNotFoundError:
            pass
        except Exception as e:
            logging.exception(e)
        pack = self.packages.get(name)
        if not pack:
            return self.put_into_queue(class_desc, timeout)
        if not version.check_version(self, pack.get(version.VERSION), class_desc.get(version.VERSION)):
            return None
        return pack.get(PACKAGE)

    def put_into_queue(self, class_desc, timeout):
        queue = asyncio.Queue()
        waiters = self.waiters.get(class_desc.get(PACKAGE_NAME))
        if not waiters:
            waiters = []
            self.waiters[class_desc.get(PACKAGE_NAME)] = waiters
            if not class_desc.get(CLASS):
                asyncio.get_running_loop().create_task(self.copy_module(class_desc))
            elif params.instance.get('developing_mode'):
                asyncio.get_running_loop().create_task(self.copy_package(class_desc))
            else:
                asyncio.get_running_loop().create_task(self.load_package(class_desc, timeout))
        waiters.append({'version': class_desc.get(version.VERSION), 'class': class_desc.get(CLASS), 'queue': queue})
        return queue

    async def load_package(self, class_desc, timeout):
        if not await self.load(class_desc, timeout):
            return
        if not self.are_packages_suitable():
            return
        await self.install(class_desc.get(PACKAGE_NAME))

    async def load(self, class_desc, timeout):
        package_name = class_desc.get(PACKAGE_NAME) + version.conditions_as_text(class_desc.get(version.VERSION))
        url = class_desc.get(URL)
        if self._load(package_name):
            return True
        recipient = self.parent.parent.adaptor.get_head_addr()
        body = {PACKAGE_NAME: package_name, URL: url}
        msg = msg_factory.get_msg('load_package', body, recipient)
        ans = await self.parent.parent.adaptor.ask(msg, timeout, self)
        if ans['command'] == 'package_is_not_loaded':
            return False
        return self._load(package_name)

    def _load(self, package_name):
        if self.download(package_name, self.source_path, self.tmp_path):
            return True
        if self.download(package_name, self.delivery_path, self.source_path):
            return self.download(package_name, self.source_path, self.tmp_path)

    def download(self, package_name, src, dst):
        res = None
        try:
            res = subprocess.check_call(
                [sys.executable, '-m', 'pip', 'download', package_name, '--disable-pip-version-check', '--no-index',
                 f'--find-links={src}', f'-d{dst}'])
        except subprocess.CalledProcessError:
            logging.warning(f'Package "{package_name}" is not in the folder "{src}"')
        if res != 0:
            dir_operations.cleardir(self.tmp_path)
        return res == 0

    def are_packages_suitable(self):
        for name in os.listdir(self.tmp_path):
            tokens = name.split('-')
            pack = self.packages.get(tokens[0])
            if not pack:
                continue
            if not version.check_version(self, pack[version.VERSION], {'==': version.from_string(tokens[1])}):
                dir_operations.cleardir(self.tmp_path)
                return False
        return True

    async def install(self, package_name):
        res = None
        try:
            res = subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install',  '--upgrade', package_name, '--no-index',
                 f'--find-links={self.tmp_path}', f'--target={self.work_path}'])
            await self.import_and_notify(package_name)
        except Exception as ex:
            logging.exception(ex)
        dir_operations.cleardir(self.tmp_path)
        return res == 0

    async def import_and_notify(self, package_name):
        for name in os.listdir(self.tmp_path):
            tokens = name.split('-')
            pack = self.packages.get(tokens[0])
            if not pack:
                ver = version.from_string(tokens[1])
                if tokens[0] == package_name:
                    pack = importlib.import_module(package_name)
                    await self.notify(package_name, ver, pack)
                self.packages[tokens[0]] = {version.VERSION: ver, PACKAGE: pack}

    async def notify(self, package_name, ver, pack):
        if not pack:
            pass
        for waiter in self.waiters.get(package_name):
            res = None
            if version.check_version(self, ver, waiter.get(version.VERSION)):
                class_name = waiter.get(CLASS)
                try:
                    res = getattr(pack, class_name) if class_name else get_primary_class(pack)
                except Exception as ex:
                    logging.exception(ex)
            await waiter['queue'].put(res)
        del self.waiters[package_name]

    async def copy_package(self, class_desc):
        package_name = class_desc.get(PACKAGE_NAME)
        path = f'{params.instance.get("plugin_dir")}/{package_name}'
        lst = [version.from_string(name) for name in os.listdir(path) if version.from_string(name)]
        ver = version.find_max_version(self, lst, class_desc.get(version.VERSION))
        src = f'{path}/{version.to_string(ver)}/{package_name}'
        dst = f'{self.work_path}/{package_name}'
        dir_operations.copy_dir(src, dst)
        pack = None
        try:
            pack = await self.import_package(package_name)
            self.packages[package_name] = {version.VERSION: ver, PACKAGE: pack}
        except Exception as e:
            logging.exception(e)
        await self.notify(package_name, ver, pack)

    async def copy_module(self, class_desc):
        package_name = class_desc.get(PACKAGE_NAME)
        src = f'{self.source_path}/{package_name}.py'
        dst = f'{self.work_path}/{package_name}.py'
        dir_operations.copy_file(src, dst)
        pack = await self.import_package(package_name)
        if not pack:
            return
        ver = None
        await self.notify(package_name, ver, pack)
        self.packages[package_name] = {version.VERSION: ver, PACKAGE: pack}

    async def import_package(self, package_name):
        importlib.invalidate_caches()
        try:
            res = importlib.import_module(package_name)
            logging.info(f'Module "{package_name}" is imported')
            return res
        except ModuleNotFoundError as e:
            logging.exception(e)

def get_primary_class(module):
    classes = inspect.getmembers(module, inspect.isclass)
    if classes:
        primary_class_name, primary_class = classes[0]
        return primary_class
    else:
        return None
