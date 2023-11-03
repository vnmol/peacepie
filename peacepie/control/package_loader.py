import asyncio
import logging
import subprocess
import sys

from peacepie import msg_factory, params
from peacepie.assist import log_util, dir_operations


class PackageLoader:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.queue = asyncio.Queue()
        self.path = f'{params.instance["package_dir"]}/source'
        dir_operations.makedir(self.path)
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def run(self, queue):
        await queue.put(msg_factory.get_msg('ready'))
        while True:
            msg = await self.queue.get()
            self.logger.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    self.logger.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                self.logger.exception(ex)

    async def handle(self, msg):
        command = msg['command']
        if command == 'load_package':
            await self.load_package(msg)
        else:
            return False
        return True

    async def load_package(self, msg):
        res = None
        try:
            args = [sys.executable, '-m', 'pip', 'download', msg['body']['package_name'],
                    '--disable-pip-version-check', f'-d{self.path}']
            if params.instance[params.EXTRA_INDEX_URL]:
                args.append(f'--{params.EXTRA_INDEX_URL}={params.instance[params.EXTRA_INDEX_URL]}')
            res = subprocess.check_call(args)
        except Exception as ex:
            self.logger.exception(ex)
        command = 'package_is_loaded' if res == 0 else 'package_is_not_loaded'
        await self.parent.connector.send(self, msg_factory.get_msg(command, recipient=msg['sender']))
