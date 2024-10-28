import asyncio
import logging
import os
import subprocess
import sys

from peacepie import params, msg_factory
from peacepie.assist import log_util, dir_operations, version

DELIVERY_DIR = 'delivery'

BLOCK_SIZE = 1024


class Delivery:

    def __init__(self, parent):
        self.parent = parent
        self.delivery_path = f'{params.instance["package_dir"]}/{DELIVERY_DIR}'
        dir_operations.makedir(self.delivery_path, True)
        self.queue = asyncio.Queue()
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self):
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'deliver_package':
            await self.deliver_package(msg)
        elif command == 'transfer':
            await self.transfer(msg)
        else:
            return False
        return True

    async def deliver_package(self, msg):
        dir_operations.cleardir(self.delivery_path)
        body = msg.get('body')
        package_desc = body.get('package_desc')
        if (not await self.download(package_desc.get('package_name'), package_desc.get(version.VERSION)) or
                not await self.send(body.get('recipient'))):
            ans = self.parent.adaptor.get_msg('package_is_not_delivered', recipient=msg.get('sender'))
            await self.parent.adaptor.send(ans)
            dir_operations.cleardir(self.delivery_path)
            return
        ans = self.parent.adaptor.get_msg('package_delivered', recipient=msg.get('sender'))
        await self.parent.adaptor.send(ans)
        dir_operations.cleardir(self.delivery_path)

    async def download(self, package_name, conditions):
        package_name = package_name + version.conditions_as_text(conditions)
        if self._download(package_name):
            return True
        recipient = self.parent.adaptor.get_head_addr()
        msg = msg_factory.get_msg('load_package', {'package_name': package_name}, recipient=recipient)
        ans = await self.parent.adaptor.ask(self, msg)
        if ans['command'] == 'package_is_not_loaded':
            return False
        return self._download(package_name)

    def _download(self, package_name):
        res = None
        try:
            res = subprocess.check_call(
                [sys.executable, '-m', 'pip', 'download', package_name, '--disable-pip-version-check', '--no-index',
                 f'--find-links={params.instance["package_dir"]}/source', f'-d{self.delivery_path}'])
        except Exception as ex:
            logging.exception(ex)
        return res == 0

    async def send(self, recipient):
        for filename in os.listdir(self.delivery_path):
            with open(f'{self.delivery_path}/{filename}', 'br') as f:
                while True:
                    data = f.read(BLOCK_SIZE)
                    if not data:
                        break
                    body = {'filename': filename, 'data': data.decode('latin-1')}
                    msg = msg_factory.get_msg('transfer', body, recipient=recipient)
                    ans = await self.parent.adaptor.ask(self, msg, 10)
                    if ans.get('command') != 'transferred':
                        return False
        return True

    async def transfer(self, msg):
        body = msg.get('body')
        with open(f'{self.delivery_path}/{body.get("filename")}', 'ba') as f:
            f.write(body.get('data').encode('latin-1'))
        await self.parent.adaptor.send(self, msg_factory.get_msg('transferred', recipient=msg.get('sender')))


