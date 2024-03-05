import asyncio
import logging
import os
import shutil

from peacepie import msg_factory, params
from peacepie.assist import log_util


class Starter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        package_path = params.instance.get('starter')
        package_name = os.path.basename(package_path)
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_source_path'))
        body = ans.get('body')
        if not body:
            return
        dst = f'{body.get("path")}/{package_name}'
        shutil.copy(package_path, dst)
        package_name = package_name.split('.')[0]
        class_desc = {'package_name': package_name, 'class': None}
        msg = msg_factory.get_msg('create_actor', {'class_desc': class_desc, 'name': 'starter'})
        ans = await self.adaptor.ask(msg)
        command = ans.get('command')
        if command != 'actor_is_created':
            return
        msg = msg_factory.get_msg('start', None, recipient=ans.get('body'))
        await self.adaptor.send(msg)
