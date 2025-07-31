import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
from functools import partial

from peacepie import msg_factory, params, loglistener
from peacepie.assist import dir_opers, json_util, log_util, version


class PackageLoader:

    def __init__(self, parent):
        self.parent = parent
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.queue = asyncio.Queue()
        self.source_path = params.instance.get('source_path')
        self.tmp_path = f'{params.instance.get("package_dir")}/tmp'
        dir_opers.makedir(self.source_path)
        dir_opers.makedir(self.tmp_path, False)
        self.loadings = {}
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
        ver, _ = await self.acquire_package(requires_dist, body.get('url'))
        if ver:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_loaded', {'ver': ver}, recipient), self)
        else:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)

    async def acquire_package(self, requires_dist, url):
        package_name = requires_dist.get('package_name')
        version_spec = requires_dist.get('version_spec')
        ver, bundle = find_version(self.source_path, package_name, version_spec)
        if ver:
            return ver, bundle
        while True:
            ver, bundle = find_version(self.tmp_path, package_name, version_spec)
            if ver:
                return ver, bundle
            package_loading = self.loadings.get(package_name)
            if package_loading is None:
                break
            else:
                queue = asyncio.Queue()
                package_loading.append(queue)
                await queue.get()
        self.loadings[package_name] = []
        ver, dependencies, output = await acquire_package(self.source_path, package_name, version_spec, url)
        if not ver:
            logging.exception(self.parent.adaptor.res_squeeze(output))
            return None
        logging.info(self.parent.adaptor.res_squeeze(output))
        tasks = [asyncio.create_task(self.acquire_package(dependency, url))
                 for dependency in dependencies if 'extra' not in dependency]
        if len(tasks) > 0:
            results = await asyncio.gather(*tasks)
            for result in results:
                bundle = bundle.union(result[1])
        for queue in self.loadings.get(package_name):
            await queue.put(None)
        del self.loadings[package_name]
        return ver, bundle

    def normalize(self):
        for entry in os.listdir(self.tmp_path):
            if not (os.path.isdir(os.path.join(self.tmp_path, entry)) and entry.endswith('.dist-info')):
                continue
            folders = set()
            with open(f'{self.tmp_path}/{entry}/RECORD', 'r', encoding='utf-8') as f:
                for line in f:
                    while line.startswith('../'):
                        line = line[3:]
                    folders.add(line[:re.search(r'[/,]', line).start()])
            ver_pack_name = entry.rsplit('.', 1)[0]
            ver_pack_path = os.path.join(self.tmp_path, ver_pack_name)
            pack_desc = ver_pack_name.split('-', 1)
            pack_name = pack_desc[0]
            pack_path = os.path.join(self.tmp_path, pack_name)
            ver = pack_desc[1]
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


async def acquire_package(path, package_name, version_spec, url):
    ver_package_name = package_name + version_spec if version_spec else package_name
    args = ([sys.executable, '-m', 'pip', 'install', '--no-deps', '--disable-pip-version-check'])
    if url:
        host = url.split("//")[-1].split("/")[0]
        args.append(f'--trusted-host={host}')
        args.append(f'--extra-index-url={url}')
    args.append(f'--target={path}/{package_name}')
    args.append(ver_package_name)
    logging.info(args)
    loop = asyncio.get_running_loop()
    try:
        output = await loop.run_in_executor(
            None,
            partial(subprocess.check_output, args, stderr=subprocess.STDOUT, text=True))
    except subprocess.CalledProcessError as e:
        return None, e.output
    dist_info_entry = None
    for entry in os.listdir(f'{path}/{package_name}'):
        if entry.endswith('.dist-info'):
            dist_info_entry = entry
            break
    if not dist_info_entry:
        return None, None, f'No ".dist-info" directory found in {package_name}'
    dist_info_path = f'{path}/{package_name}/{dist_info_entry}'
    ver = None
    requires_dist = []
    with open(f'{dist_info_path}/METADATA', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('Version:'):
                ver = line.split(':', 1)[1].strip()
                if line.startswith('Requires-Dist:'):
                    requires_dist.append(version.parse_requires_dist(line.split('Requires-Dist:')[1].strip()))
    if not ver:
        return None, None, 'Version not found in METADATA file'
    rename_entry(f'{path}/{package_name}', f'{path}/{package_name}-{ver}')
    return ver, requires_dist, output


def find_version(path, package_name, version_spec):
    package_name = package_name.replace('-', '_')
    pattern = re.compile(rf'^{re.escape(package_name)}-(?P<version>.+?)\.dist-info$')
    vers = []
    for entry in os.listdir(path):
        match = pattern.match(entry)
        if match:
            vers.append(match.group('version'))
    ver = version.find_max_version(vers, version_spec)
    bundle = set()
    if ver:
        bundle_path = f'{path}/{package_name}-{ver}.dist-info/BUNDLE'
        if os.path.exists(bundle_path):
            with open(bundle_path, 'r', encoding='utf-8') as file:
                bundle.update([entry.strip() for entry in file.readlines()])
        else:
            bundle.add(f'{package_name}-{ver}')
    return ver, bundle


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
