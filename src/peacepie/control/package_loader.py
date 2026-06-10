import asyncio
import logging
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from peacepie import msg_factory, params
from peacepie.assist import dir_opers, log_util, pack_installer, pack_resolver, repo_reader


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
        self.cache_path = f'{params.instance["package_dir"]}/cache'
        dir_opers.makedir(self.cache_path, clear=False)
        self.max_retries = int(params.get_param('max_retries', 3))
        self.repo_reader = repo_reader.RepoReader(self)
        self.resolver = pack_resolver.PackResolver(self)
        self.installer = pack_installer.PackInstaller(self)
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

    async def exit(self):
        await self.resolver.exit()
        await self.installer.exit()

    async def handle(self, msg):
        command = msg['command']
        if command == 'load_package':
            await self.load_package(msg)
        else:
            return False
        return True

    async def load_package(self, msg):
        dir_opers.makedir(self.tmp_path, clear=True)
        recipient = msg.get('sender')
        body = msg.get('body')
        index_url = body.get('index_url') if body.get('index_url') else params.instance.get('index-url')
        requirement = Requirement(body.get('requires_dist'))
        requirement.name = canonicalize_name(requirement.name)
        package_version = self.get_version(requirement)
        if package_version:
            body = {'package_version': package_version}
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_loaded', body, recipient), self)
            return
        packs = await self.resolver.resolve_package(index_url, requirement)
        if packs is None:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)
            return
        if await self.installer.install_packages(packs):
            body = {'package_version': self.get_version_from_tree()}
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_loaded', body, recipient), self)
        else:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)

    def get_version(self, requirement):
        package_name = requirement.name.replace('-', '_')
        entries = [p.name for p in Path(self.source_path).iterdir() if p.is_dir() and p.name.startswith(package_name)]
        reference_book = {}
        for entry in entries:
            entry_name, entry_version = entry.split('-')
            if reference_book.get(entry_version) is None:
                reference_book[entry_version] = {entry_name}
            else:
                reference_book[entry_version].add(entry_name)
        reference_book = dict(sorted(reference_book.items(), reverse=True))
        for ver, names in reference_book.items():
            if ver not in requirement.specifier:
                continue
            if package_name not in names:
                continue
            if requirement.extras is None:
                return ver
            for extra in requirement.extras:
                if f'{package_name}[{extra}]' not in names:
                    break
            else:
                return ver
        return None

    def get_version_from_tree(self):
        for child in self.resolver.tree.children:
            return str(child.data.get('package_version'))
        return None
