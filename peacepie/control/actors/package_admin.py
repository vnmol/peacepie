import asyncio
import importlib
import logging
import os
import subprocess
import sys

from peacepie import params, msg_factory
from peacepie.assist import log_util, version, dir_operations

CLASS = 'class'
PACKAGE = 'package'
PACKAGE_NAME = 'package_name'


class PackageAdmin:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.packages = {}
        self.waiters = {}
        self.tmp_path = f'{params.instance["package_dir"]}/tmp/{self.parent.parent.process_name}'
        dir_operations.makedir(self.tmp_path, True)
        self.work_path = f'{params.instance["package_dir"]}/work/{self.parent.parent.process_name}'
        dir_operations.makedir(self.work_path, True)
        self.logger.info(log_util.get_alias(self) + ' is created')

    def get_class(self, class_desc):
        res = self.get_package(class_desc)
        if isinstance(res, asyncio.Queue):
            return res
        try:
            res = getattr(res, class_desc[CLASS])
        except Exception as ex:
            self.logger.exception(ex)
            return None
        return res

    def get_package(self, class_desc):
        pack = self.packages.get(class_desc[PACKAGE_NAME])
        if not pack:
            return self.put_into_queue(class_desc)
        if not version.check_version(self, pack[version.VERSION], class_desc.get(version.VERSION)):
            return None
        return pack[PACKAGE]

    def put_into_queue(self, class_desc):
        queue = asyncio.Queue()
        waiters = self.waiters.get(class_desc[PACKAGE_NAME])
        if not waiters:
            waiters = []
            self.waiters[class_desc[PACKAGE_NAME]] = waiters
            asyncio.get_running_loop().create_task(self.load_package(class_desc))
        waiters.append({'version': class_desc.get(version.VERSION), 'class': class_desc[CLASS], 'queue': queue})
        return queue

    async def load_package(self, class_desc):
        if not await self.download(class_desc[PACKAGE_NAME], class_desc.get(version.VERSION)):
            return
        if not self.are_packages_suitable():
            return
        await self.install(class_desc[PACKAGE_NAME])

    async def download(self, package_name, conditions):
        package_name = package_name + version.conditions_as_text(conditions)
        if self._download(package_name):
            return True
        dir_operations.cleardir(self.tmp_path)
        recipient = self.parent.parent.connector.get_head_addr()
        msg = msg_factory.get_msg('load_package', {'package_name': package_name}, recipient=recipient)
        ans = await self.parent.parent.connector.ask(self, msg)
        if ans['command'] == 'package_is_not_loaded':
            return False
        return self._download(package_name)

    def _download(self, package_name):
        res = None
        try:
            res = subprocess.check_call(
                [sys.executable, '-m', 'pip', 'download', package_name, '--disable-pip-version-check', '--no-index',
                 f'--find-links={params.instance["package_dir"]}/source', f'-d{self.tmp_path}'])
        except Exception as ex:
            self.logger.exception(ex)
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
                [sys.executable, '-m', 'pip', 'install', package_name, '--no-index',
                 f'--find-links={self.tmp_path}', f'--target={self.work_path}'])
            await self.import_and_notify(package_name)
        except Exception as ex:
            self.logger.exception(ex)
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
        for waiter in self.waiters.get(package_name):
            res = None
            if version.check_version(self, ver, waiter[version.VERSION]):
                try:
                    res = getattr(pack, waiter[CLASS])
                except Exception as ex:
                    self.logger.exception(ex)
            await waiter['queue'].put(res)
        del self.waiters[package_name]
