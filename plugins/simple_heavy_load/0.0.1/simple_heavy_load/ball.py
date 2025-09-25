import asyncio
import logging
import random
import threading
import time

from src.peacepie.assist import timer


class Ball:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        elif command == 'timer':
            await self.timer()
        else:
            return False
        return True

    async def start(self):
        print(self.adaptor.get_node(), self.adaptor.get_caller_info())
        timer.start(4, self.adaptor.queue, None)

    async def timer(self):
        nodes = await self.adaptor.get_all_nodes()
        nodes.remove(self.adaptor.get_node())
        body = {'node': random.choice(nodes), 'entity': self.adaptor.name}
        await self.adaptor.send(self.adaptor.get_msg('recreate_actor', body))
