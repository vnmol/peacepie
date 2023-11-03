import asyncio
import logging

from peacepie import msg_factory
from peacepie.assist import log_util
from peacepie.control import prime_admin


class Spy:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.logger.info(log_util.get_alias(self) + ' is created')

    def handle(self, msg):
        self.logger.debug(log_util.async_received_log(self, msg))
        if msg.command == 'gather_info':
            self.gather_info(msg)
        elif msg.command == 'get_info':
            self.get_info(msg)
        elif msg.command == 'info':
            self.info(msg)
        else:
            self.logger.warning(log_util.get_alias(self) + ' The message is not handled: ' + str(msg))

    def gather_info(self, msg):
        asyncio.get_running_loop().create_task(self.gathering(msg))

    async def gathering(self, msg):
        message = msg_factory.get_msg('get_info', msg.body)
        with_delta = 'delta' in msg.body['fields']
        messages = await self.parent.connector.ask_admins(self, message, None, with_delta=with_delta)
        res = []
        for message in messages:
            body = message['msg'].body
            body['sender'] = message['msg'].sender
            if with_delta:
                body['delta'] = message['delta']
            res.append(body)
        message = msg_factory.get_msg('info', res, recipient=msg.sender)
        await self.parent.connector.send(self, message)

    def get_info(self, msg):
        asyncio.get_running_loop().create_task(self.getting(msg))

    async def getting(self, msg):
        body = {}
        try:
            for field in msg.body['fields']:
                if field == 'is_loaded':
                    body[field] = await self.is_loaded(msg.body['params']['class_desc'])
                elif field == 'is_available':
                    body[field] = await self.is_available(msg.body['params']['class_desc'])
                elif field == 'can_deploy':
                    body[field] = await self.can_deploy(msg.body['params'])
                elif field == 'max_queue_length':
                    body[field] = self.max_queue_length()
                elif field == 'queue_length_sum':
                    body[field] = self.queue_length_sum()
                elif field == 'count':
                    body[field] = len(self.parent.actors)
                elif field == 'host':
                    body[field] = self.parent.host_name
                elif field == 'is_prime':
                    body[field] = isinstance(self.parent, prime_admin.PrimeAdmin)
        except Exception as e:
            self.logger.exception(e)
        message = msg_factory.get_msg('info', body, recipient=msg.sender, sender=self.parent.adaptor.name)
        await self.parent.connector.send(self, message)

    async def is_loaded(self, class_desc):
        return self.parent.actor_admin.package_admin.is_loaded(class_desc)

    async def is_available(self, class_desc):
        return await self.parent.actor_admin.package_admin.is_available(class_desc)

    async def can_deploy(self, params):
        package_name = params['class_desc']['package_name']
        dependency_desc = params['dependency_desc']
        return await self.parent.actor_admin.package_admin.can_deploy(package_name, dependency_desc)

    def max_queue_length(self):
        res = 0
        for actor in self.parent.actors.values():
            if actor['adaptor'].queue.qsize() > res:
                res = actor['adaptor'].queue.qsize()
        return res

    def queue_length_sum(self):
        res = 0
        for actor in self.parent.actors.values():
            res += actor['adaptor'].queue.qsize()
        return res

    def info(self, msg):
        asyncio.get_running_loop().create_task(self.informing(msg))

    async def informing(self, msg):
        pass
