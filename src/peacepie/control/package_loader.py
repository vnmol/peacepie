import asyncio
import logging
import os
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
        dir_opers.makedir(self.source_path, params.instance.get('clear_source_on_restart'))
        self.tmp_path = f'{params.instance["package_dir"]}/tmp'
        dir_opers.makedir(self.tmp_path, clear=True)
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
        timeout = msg.get('timeout')
        body = msg.get('body')
        requires_dist = body.get('requires_dist')
        dir_opers.makedir(self.tmp_path, clear=True)
        bundle = await self.acquire_package(requires_dist, body.get('url'), timeout)
        if bundle:
            self.move_packages()
            body = {'bundle': list(bundle)}
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_loaded', body, recipient), self)
        else:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)

    def move_packages(self):
        for package in os.listdir(self.tmp_path):
            dir_opers.move_dir(f'{self.tmp_path}/{package}', f'{self.source_path}/{package}')

    async def acquire_package(self, requires_dist, url, timeout):
        package_name = requires_dist.get('package_name')
        version_spec = requires_dist.get('version_spec')
        package_loading = self.loadings.get(package_name)
        if package_loading is None:
            bundle = self.find_bundle(package_name, version_spec)
            if bundle:
                return bundle
        else:
            queue = asyncio.Queue()
            package_loading.append(queue)
            await queue.get()
            return self.find_bundle(package_name, version_spec)
        self.loadings[package_name] = []
        await self.install_package(package_name, version_spec, url, timeout)
        ver, dependencies = self.find_version_with_dependencies(package_name, version_spec)
        logging.info(f'For package "{package_name}-{ver}" dependencies are found: {dependencies}')
        if not ver:
            return None
        bundle = {f'{package_name}-{ver}'}
        tasks = [asyncio.create_task(self.acquire_package(dependency, url, timeout))
                 for dependency in dependencies]
        if len(tasks) > 0:
            results = await asyncio.gather(*tasks)
            for result in results:
                if result is None:
                    return None
                bundle = bundle.union(result)
        self.save_bundle(package_name, ver, bundle)
        for queue in self.loadings.get(package_name):
            await queue.put(None)
        del self.loadings[package_name]
        return bundle

    def find_bundle(self, package_name, version_spec):
        res = self._find_bundle(self.source_path, package_name, version_spec)
        if res:
            return res
        return self._find_bundle(self.tmp_path, package_name, version_spec)

    def _find_bundle(self, path, package_name, version_spec):
        ver = None
        bundle = None
        for pack in os.listdir(path):
            pack_path = f'{path}/{pack}'
            for entry in os.listdir(pack_path):
                entry_path = f'{pack_path}/{entry}'
                if not (os.path.isdir(entry_path) and entry.endswith('.dist-info')):
                    continue
                name, v, _ = dir_opers.get_metadata(entry_path)
                if name.lower().replace('-', '_') == package_name.lower().replace('-', '_'):
                    if version.check_version(v, version_spec):
                        if ver is None or version.check_version(v, f'>{ver}'):
                            ver = v
                            bundle = get_bundle(entry_path)
        return bundle

    def find_version_with_dependencies(self, package_name, version_spec):
        ver = None
        dependencies = None
        for pack in os.listdir(self.tmp_path):
            pack_path = f'{self.tmp_path}/{pack}'
            for entry in os.listdir(pack_path):
                entry_path = f'{pack_path}/{entry}'
                if not (os.path.isdir(entry_path) and entry.endswith('.dist-info')):
                    continue
                name, v, ds = dir_opers.get_metadata(entry_path)
                if name.lower().replace('-', '_') == package_name.lower().replace('-', '_'):
                    if version.check_version(v, version_spec):
                        if ver is None or version.check_version(v, f'>{ver}'):
                            ver = v
                            dependencies = ds
                    if not pack_path.endswith(f'-{v}'):
                        dir_opers.rename_dir(pack_path, f'{pack_path}-{v}')
        return ver, dependencies

    async def install_package(self, package_name, version_spec, url, timeout):
        ver_package_name = package_name + version_spec if version_spec else package_name
        args = ([sys.executable, '-m', 'pip', 'install', '--no-deps', '--disable-pip-version-check'])
        if url:
            host = url.split("//")[-1].split("/")[0]
            args.append(f'--trusted-host={host}')
            args.append(f'--extra-index-url={url}')
        args.append(f'--target={self.tmp_path}/{package_name}')
        args.append(ver_package_name)
        logging.info(args)
        loop = asyncio.get_running_loop()
        try:
            output = await asyncio.wait_for(
                loop.run_in_executor(None,
                                     partial(subprocess.check_output,args, stderr=subprocess.STDOUT, text=True)),
                timeout=timeout
            )
            logging.info(self.parent.adaptor.res_squeeze(output))
        except Exception as e:
            logging.exception(e)

    def save_bundle(self, package_name, package_ver, bundle):
        for package in os.listdir(self.tmp_path):
            package_path = f'{self.tmp_path}/{package}'
            for entry in os.listdir(package_path):
                entry_path = f'{package_path}/{entry}'
                if not (os.path.isdir(entry_path) and entry.endswith('.dist-info')):
                    continue
                name, ver, _ = dir_opers.get_metadata(entry_path)
                if name.lower().replace('-', '_') == package_name.lower().replace('-', '_') and ver == package_ver:
                    lines = list(bundle)
                    lines.sort()
                    with open(f'{entry_path}/BUNDLE', 'w', encoding='utf-8') as f:
                        f.writelines(line + '\n' for line in lines)
                    logging.info(f'BUNDLE is saved to {entry_path}')
                    return


def get_bundle(path):
    try:
        with open(f'{path}/BUNDLE', 'r', encoding='utf-8') as f:
            bundle = [line.strip() for line in f.readlines()]
        return bundle
    except Exception as e:
        logging.exception(e)
