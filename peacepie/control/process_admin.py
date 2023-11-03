import asyncio
import logging
import multiprocessing
from logging.handlers import QueueHandler

from peacepie import msg_factory, loglistener, multimanager, params, adaptor
from peacepie.assist import log_util, misc
from peacepie.control import admin


class ProcessAdmin:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.processes = {}
        self.process_index = 0
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def create_process(self, sender):
        name = misc.ComplexName(self.parent.host_name, f'process_{self.process_index}', 'admin')
        self.process_index += 1
        p = multiprocessing.Process(
            target=create,
            args=(self.parent.adaptor.name, name, params.instance,
                  msg_factory.instance.get_queue(), loglistener.instance.get_log_desc(), sender))
        p.start()
        self.processes[name] = p


def create(lord, name, prms, msg_queue, log_desc, sender):
    params.instance = prms
    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])
    logger.addHandler(QueueHandler(log_desc.queue))
    logger.setLevel(log_desc.level)
    prefix = f'{name.host_name}.{name.process_name}'
    multimanager.init_multimanager(f'{prefix}.multimanager')
    msg_factory.init_msg_factory(name.host_name, name.process_name, 'msg_factory', msg_queue)
    performer = admin.Admin(lord, name.host_name, name.process_name)
    actr = None
    try:
        actr = adaptor.Adaptor(name.get_actor_name(), None, performer, sender)
        asyncio.run(actr.run())
    except KeyboardInterrupt as ki:
        logger.warning(ki.__repr__())
    except BaseException as ex:
        logger.exception(ex)
    finally:
        logger.info(f'{log_util.get_alias(actr)} is stopped')
