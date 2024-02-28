import asyncio
import logging
import os
import shutil

from peacepie import msg_factory, params
from peacepie.assist import log_util


class Starter:

    def __init__(self, parent):
        self.parent = parent
        logging.info(log_util.get_alias(self) + ' is created')

    async def start(self):
        package_path = params.instance.get('starter')
        package_name = os.path.basename(package_path)
        dst = f'{self.parent.package_admin.source_path}/{package_name}'
        shutil.copy(package_path, dst)
        package_name = package_name.split('.')[0]
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.listening(queue))
        class_desc = {'package_name': package_name, 'class': None}
        msg = msg_factory.get_msg('create_actor', {'class_desc': class_desc, 'name': 'starter'})
        msg['sender'] = queue
        await self.parent.parent.connector.send(self, msg)

    async def listening(self, queue):
        ans = await queue.get()
        logging.debug(f'{log_util.get_alias(self)} received: {ans}')
        command = ans.get('command')
        if command != 'actor_is_created':
            return
        try:
            msg = msg_factory.get_msg('start', None, recipient=ans.get('body'))
            await self.parent.parent.connector.send(self, msg)
        except Exception as e:
            logging.exception(e)
