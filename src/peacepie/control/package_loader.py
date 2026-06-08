import asyncio
import logging

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
        packs = await self.resolver.resolve_package(index_url, requirement)
        if packs is None:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)
            return
        if await self.installer.install_packages(packs):
            body = {'package_version': self.get_version()}
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_loaded', body, recipient), self)
        else:
            await self.parent.adaptor.send(msg_factory.get_msg('package_is_not_loaded', None, recipient), self)

    def get_version(self):
        for child in self.resolver.tree.children:
            return str(child.data.get('package_version'))
        return None
