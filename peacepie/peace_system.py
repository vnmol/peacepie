import asyncio
import logging

import uvloop

from peacepie import adaptor, params, multimanager, loglistener, msg_factory, log_conf
from peacepie.assist import log_util
from peacepie.control import head_prime_admin, prime_admin


instance = None


class PeaceSystem:

    def __init__(self):
        global instance
        instance = self
        params.init_params()
        log_conf.logger_start(params.instance.get('log_config'))
        self.is_head = params.instance.get('intra_role') == 'master'
        self.host_name = params.instance.get('host_name')
        self.process_name = params.instance.get('process_name')
        self.prefix = self.host_name + '.' + self.process_name + '.'
        multimanager.init_multimanager(self.prefix + 'multimanager')
        loglistener.init_loglistener(self.prefix + 'loglistener')
        self.logger = logging.getLogger()
        self.name = self.prefix + 'system'
        self.task = None
        msg_queue = multimanager.instance.get_queue()
        msg_queue.put(0)
        msg_factory.init_msg_factory(self.host_name, self.process_name, 'msg_factory', msg_queue)
        self.logger.info(log_util.get_alias(self) + ' is created')

    def start(self):
        try:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            if self.is_head:
                performer = head_prime_admin.HeadPrimeAdmin(self.host_name, self.process_name)
            else:
                performer = prime_admin.PrimeAdmin(self.host_name, self.process_name)
            actr = adaptor.Adaptor(self.prefix + 'admin', None, performer)
            asyncio.run(actr.run())
        except KeyboardInterrupt as ki:
            self.logger.warning(ki.__repr__())
        except BaseException as ex:
            self.logger.exception(ex)
        finally:
            self.logger.info(log_util.get_alias(self) + ' is stopped')
            loglistener.instance.stop()

    async def _start(self):
        await self.task
