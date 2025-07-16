import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
from functools import partial

from peacepie import msg_factory, params, loglistener
from peacepie.assist import dir_operations, json_util, log_util, version


class PackageLoader:

    def __init__(self, parent):
        self.parent = parent
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.queue = asyncio.Queue()
        self.source_path = params.instance.get('source_path')
        self.tmp_path = f'{params.instance.get("package_dir")}/tmp'
        dir_operations.makedir(self.source_path)
        dir_operations.makedir(self.tmp_path, False)
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self, queue):
        await queue.put(msg_factory.get_msg('ready'))
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

    async def handle(self, msg):
        command = msg['command']
        if command == 'load_package':
            await self.load_package(msg)
        else:
            return False
        return True

    async def load_package(self, msg):
        recipient = msg.get('sender')
        body = msg.get('body')
        requires_dist = body.get('requires_dist')
        package_name = requires_dist.get('package_name')
        version_spec = requires_dist.get('version_spec')
        ver = self.find_version(package_name, version_spec)
        if not ver:
            ver = await self.acquire_package(requires_dist, body.get('url'))
        if ver:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_loaded', {'ver': ver}, recipient), self)
        else:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)

    def find_version(self, package_name, version_spec):
        pattern = rf'^{re.escape(package_name)}-(?P<version>\d+\.\d+\.\d+)$'
        vers = []
        for entry in os.listdir(self.source_path):
            match = re.fullmatch(pattern, entry)
            if match:
                vers.append(match.group('version'))
        res = version.find_max_version(vers, version_spec)
        if res:
            res = version.version_to_string(res)
        return res

    async def acquire_package(self, requires_dist, url):
        package_name = requires_dist.get('package_name')
        version_spec = requires_dist.get('version_spec')
        ver_package_name = package_name + version_spec if version_spec else package_name
        host = url.split("//")[-1].split("/")[0]
        args = ([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check'])
        if url:
            args.append(f'--trusted-host={host}')
            args.append(f'--extra-index-url={url}')
        args.append(f'--target={self.tmp_path}')
        args.append(ver_package_name)
        logging.info(args)
        res = await acquire_package(args)
        if res[0]:
            logging.info(self.parent.adaptor.res_squeeze(res[1]))
        else:
            logging.exception(self.parent.adaptor.res_squeeze(res[1]))
        ver = self.normalize(package_name)
        self.shift()
        return ver

    def normalize(self, package_name):
        res = None
        for entry in os.listdir(self.tmp_path):
            if not (os.path.isdir(os.path.join(self.tmp_path, entry)) and entry.endswith('.dist-info')):
                continue
            ver_pack_name = entry.rsplit('.', 1)[0]
            ver_pack_path = os.path.join(self.tmp_path, ver_pack_name)
            pack_desc = ver_pack_name.split('-', 1)
            pack_name = pack_desc[0]
            pack_path = os.path.join(self.tmp_path, pack_name)
            ver = pack_desc[1]
            if pack_name == package_name:
                res = ver
            ver_module_name = pack_name + '.py-' + ver
            ver_module_path = os.path.join(self.tmp_path, ver_module_name)
            module_name = pack_name + '.py'
            module_path = os.path.join(self.tmp_path, module_name)
            if os.path.exists(pack_path):
                remove_entry(ver_pack_path)
                remove_entry(module_path)
                remove_entry(ver_module_path)
                rename_entry(pack_path, ver_pack_path)
            elif os.path.exists(module_path):
                remove_entry(ver_pack_path)
                remove_entry(ver_module_path)
                rename_entry(module_path, ver_module_path)
        entries = os.listdir(self.tmp_path)
        entries = [entry for entry in entries if not self.is_correct_entry(entry)]
        for entry in entries:
            remove_entry(os.path.join(self.tmp_path, entry))
        entries = os.listdir(self.tmp_path)
        entries = [f'{entry}\n' for entry in entries if not entry.endswith('.dist-info')]
        file_name = f'{package_name}-{res}.dist-info/BUNDLE'
        with open(os.path.join(self.tmp_path, file_name), 'w', encoding='utf-8') as f:
            f.writelines(entries)
        return res

    def is_correct_entry(self, entry):
        if entry.endswith('.dist-info'):
            return True
        if os.path.exists(os.path.join(self.tmp_path, entry) + '.dist-info'):
            return True
        entries = entry.rsplit('-', 1)
        if len(entries) != 2:
            return False
        entry = entries[0].rsplit('.py')[0] + '-' + entries[1] + '.dist-info'
        if os.path.exists(os.path.join(self.tmp_path, entry)):
            return True
        return False

    def shift(self):
        entries = os.listdir(self.tmp_path)
        entries = [entry for entry in entries if entry.endswith('.dist-info')]
        for entry in entries:
            ver_package_name = entry.rsplit('.', 1)[0]
            tokens = ver_package_name.rsplit('-', 1)
            ver_module_name = tokens[0] + '.py-' + tokens[1]
            if os.path.exists(os.path.join(self.source_path, entry)):
                remove_entry(os.path.join(self.tmp_path, entry))
                remove_entry(os.path.join(self.tmp_path, ver_package_name))
                remove_entry(os.path.join(self.tmp_path, ver_module_name))
            else:
                shift_entry(os.path.join(self.tmp_path, entry), os.path.join(self.source_path, entry))
                shift_entry(os.path.join(self.tmp_path, ver_package_name),
                            os.path.join(self.source_path, ver_package_name))
                shift_entry(os.path.join(self.tmp_path, ver_module_name),
                            os.path.join(self.source_path, ver_module_name))


async def acquire_package(args):
    loop = asyncio.get_running_loop()
    try:
        output = await loop.run_in_executor(
            None,
            partial(subprocess.check_output, args, stderr=subprocess.STDOUT, text=True))
        return True, output
    except subprocess.CalledProcessError as e:
        return False, e.output

def rename_entry(old_path, new_path):
    if not os.path.exists(old_path):
        return
    try:
        os.rename(old_path, new_path)
        logging.info(f'File "{old_path}" successfully renamed to "{new_path}"')
    except Exception as e:
        logging.exception(e)


def remove_entry(path):
    if not os.path.exists(path):
        return
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            logging.info(f'Folder "{path}" is deleted')
        else:
            os.remove(path)
            logging.info(f'File "{path}" is deleted')
    except Exception as e:
        logging.exception(e)


def shift_entry(old_path, new_path):
    if not os.path.exists(old_path):
        return
    try:
        shutil.move(old_path, new_path)
        logging.info(f'Folder/file "{old_path}" is shifted to "{new_path}"')
    except Exception as e:
        logging.exception(e)
