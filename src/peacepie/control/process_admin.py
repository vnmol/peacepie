import asyncio
import json
import logging
import logging.config
import multiprocessing
import os
import sys
from logging.handlers import QueueHandler

from peacepie import msg_factory, loglistener, multimanager, params, adaptor
from peacepie.assist import log_util, misc
from peacepie.control import admin


class ProcessAdmin:

    def __init__(self, parent):
        self.logger = logging.getLogger()
        self.parent = parent
        self.process_details = {}
        self.process_index = 0
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def exit(self):
        await asyncio.gather(*[self.remove_process(complex_name) for complex_name in self.process_details])

    async def remove_process(self, complex_name):
        details = self.process_details.get(complex_name)
        if not details:
            return
        process = details.get('process')
        event = details.get('event')
        node = complex_name.get_actor_name()
        await self.parent.adaptor.send(msg_factory.get_msg('remove_process', None, node))
        await asyncio.to_thread(event.wait, timeout=0.4)
        await asyncio.sleep(0.1)
        if process.is_alive():
            process.terminate()
            try:
                await asyncio.to_thread(process.join, timeout=0.4)
            except asyncio.TimeoutError:
                process.kill()
                await asyncio.to_thread(process.join, timeout=0.4)
        self.process_details.pop(complex_name, None)

    def get_members(self):
        res = [process.get_actor_name() for process in self.process_details]
        res.append(self.parent.adaptor.name)
        res.sort()
        return res

    async def create_process(self, recipient):
        name = misc.ComplexName(self.parent.host_name, f'process_{self.process_index}', 'admin')
        event = multiprocessing.Event()
        self.process_index += 1
        p = multiprocessing.Process(
            target=create,
            args=(self.parent.adaptor.name, name, event, params.instance,
                  msg_factory.instance.get_queue(), loglistener.instance.get_log_desc(), recipient))
        p.start()
        self.process_details[name] = {'process': p, 'event': event}


def create(lord, name, event, prms, msg_queue, log_desc, recipient):
    params.instance = prms
    if params.instance.get('separate_log_per_process'):
        log_config()
    else:
        logger = logging.getLogger()
        while logger.hasHandlers():
            logger.removeHandler(logger.handlers[0])
        logger.addHandler(QueueHandler(log_desc.queue))
        logger.setLevel(log_desc.level)
    prefix = f'{name.host_name}.{name.process_name}'
    multimanager.init_multimanager(f'{prefix}.multimanager')
    msg_factory.init_msg_factory(name.host_name, name.process_name, 'msg_factory', msg_queue)
    performer = admin.Admin(lord, name.host_name, name.process_name, event, log_desc)
    try:
        actr = adaptor.Adaptor(None, name.get_actor_name(), None, performer, recipient)
        asyncio.run(actr.run())
    except KeyboardInterrupt:
        pass
    except BaseException as ex:
        logging.exception(ex)


def log_config():
    config_filename = params.instance.get('log_config')
    process = ''
    if params.instance.get('separate_log_per_process'):
        process = f'/{multiprocessing.current_process().name}'
    try:
        with open(config_filename) as f:
            config = json.load(f)
        for _, handler_config in config.get('handlers', {}).items():
            if 'filename' in handler_config:
                handler_config['filename'] = f'{params.instance.get("log_dir")}{process}/{handler_config["filename"]}'
        check_paths(config)
        logging.config.dictConfig(config)
    except BaseException as ex:
        logging.exception(ex)


def check_paths(config):
    filenames = set([handler.get('filename') for handler in config.get('handlers').values()])
    filepaths = set([os.path.dirname(filename) for filename in filenames])
    for filepath in filepaths:
        if not os.path.exists(filepath):
            os.makedirs(filepath)
    if params.instance.get('developing_mode') or 'pycharm' in sys.executable.lower():
        for filename in filenames:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass

