import asyncio
import logging

from peacepie import params, msg_factory
from peacepie.assist import json_util, log_util


class Starter:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.queue = asyncio.Queue()
        self.is_wait = True
        self.class_desc = json_util.json_loads(params.instance.get('starter'))
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def start(self):
        asyncio.get_running_loop().create_task(self.listening())
        msg = msg_factory.get_msg('create_actor', self.class_desc,
                                  recipient=self.parent.parent.adaptor.queue, sender=self.queue)
        await self.parent.parent.connector.send(self, msg)

    async def listening(self):
        msg = await self.queue.get()
        self.logger.debug(f'{log_util.get_alias(self)} received: {msg}')
        if msg['command'] != 'actor_is_created':
            return
        self.is_wait = False
        try:
            com = json_util.json_loads(params.instance.get('start_command'))
            msg = msg_factory.get_msg(com.get('command'), com.get('body'), recipient=self.class_desc['name'])
            await self.parent.parent.connector.send(self, msg)
        except Exception as e:
            self.logger.exception(e)
