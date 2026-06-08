import asyncio
import logging
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

import installer
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile

from peacepie.assist import dir_opers


class PackInstaller:

    def __init__(self, parent):
        self.parent = parent
        self.exit_flag = False
        self.queue = None

    async def exit(self):
        self.exit_flag = True
        if self.queue:
            await self.queue.get()

    async def install_packages(self, packs):
        logging.info('Start packages installing')
        self.queue = asyncio.Queue()
        semaphore = asyncio.Semaphore(4)
        res = False
        try:
            async with asyncio.TaskGroup() as tg:
                for key, val in packs.items():
                    async def bounded_install(k=key, v=val):
                        async with semaphore:
                            await asyncio.to_thread(self._install_package, k, v)
                    tg.create_task(bounded_install())
            for package in os.listdir(self.parent.tmp_path):
                dir_opers.move_dir(f'{self.parent.tmp_path}/{package}', f'{self.parent.source_path}/{package}')
            res = True
        except Exception as e:
            logging.exception(e)
        if self.exit_flag:
            await self.queue.put(1)
        else:
            self.queue = None
        logging.info('Finish packages installing')
        return res

    def _install_package(self, key, val):
        package_name = f'{key[0]}-{val.get("version")}'
        if key[1]:
            self._install(None, key, val)
            return
        for attempt in range(self.parent.max_retries):
            if self.exit_flag:
                logging.debug(f'Exit from attempting for {package_name}')
                return
            try:
                logging.debug(f'Try {attempt + 1} to install package: {package_name}')
                if self._download_and_install(key, val):
                    logging.debug(f'Package {package_name} is installed')
                return
            except Exception as e:
                logging.error(f'For package {package_name} is error: {e}')
                if attempt + 1 == self.parent.max_retries:
                    raise

    def _download_and_install(self, key, val):
        wheel_path = self.parent.repo_reader.get_wheel(val.get('url'), key[0], val.get('version'))
        self._install(wheel_path, key, val)
        return True

    def _install(self, wheel_path, key, val):
        bundle = ''
        for dep in val.get('bundle'):
            bundle += f'{dep}\r\n'
        if key[1]:
            self._create_extra(key, val, bundle)
            return
        base = os.path.join(self.parent.tmp_path, f'{key[0]}-{val.get("version")}')
        os.makedirs(str(base), exist_ok=True)
        scheme = {
            'purelib': base,
            'platlib': base,
            'headers': os.path.join(base, 'headers'),
            'scripts': os.path.join(base, 'bin'),
            'data': os.path.join(base, 'data'),
        }
        metadata = {'BUNDLE': bundle.encode('utf-8')}
        with WheelFile.open(wheel_path) as source:
            destination = SchemeDictionaryDestination(
                scheme,
                interpreter=sys.executable,
                script_kind='posix',
            )
            installer.install(
                source=source,
                destination=destination,
                additional_metadata=metadata
            )

    def _create_extra(self, key, val, bundle):
        package_name = f'{key[0]}[{key[1]}]'
        package_version = val.get('version')
        base = os.path.join(self.parent.tmp_path, f'{package_name}-{package_version}')
        name = Path(base).name
        dist_info_dir = os.path.join(base, f'{name}.dist-info')
        os.makedirs(dist_info_dir, exist_ok=True)
        bundle_file = os.path.join(dist_info_dir, 'BUNDLE')
        with open(bundle_file, 'w', encoding='utf-8') as f:
            f.write(bundle)
        meatadata_file = os.path.join(dist_info_dir, 'METADATA')
        with open(meatadata_file, 'w', encoding='utf-8') as f:
            f.write(f'Name: {package_name}\r\n')
            f.write(f'Version: {package_version}\r\n')
            for requirement in val.get('metadata'):
                f.write(f'Requires-Dist: {str(requirement)}\r\n')
