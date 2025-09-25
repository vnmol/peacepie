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
        self.processes = {}
        self.process_index = 0
        self.logger.info(log_util.get_alias(self) + ' is created')

    async def exit(self):
        await asyncio.gather(*[self.remove_process(complex_name) for complex_name in self.processes])

    def join_process(self, process):
        return process.join(timeout=4)

    async def remove_process(self, complex_name):
        process = self.processes.get(complex_name)
        node = complex_name.get_actor_name()
        if not process:
            logging.warning(f'The process for "{node}" is not found')
            return
        self.processes.pop(complex_name, None)
        await self.parent.adaptor.send(msg_factory.get_msg('remove_process', None, node))
        await asyncio.wait_for(
            asyncio.to_thread(self.join_process, process),
            timeout=5
        )
        if not process.is_alive():
            logging.info(f'The process for "{node}" is successfully completed')
            return
        process.terminate()
        try:
            await asyncio.to_thread(process.join, timeout=1)
            logging.info(f'The process for "{node}" is terminated')
        except asyncio.TimeoutError:
            process.kill()
            await asyncio.to_thread(process.join, timeout=1)
            logging.info(f'The process for "{node}" is killed')

    def get_members(self):
        res = [process.get_actor_name() for process in self.processes]
        res.append(self.parent.adaptor.name)
        res.sort()
        return res

    async def create_process(self, recipient):
        name = misc.ComplexName(self.parent.host_name, f'process_{self.process_index}', 'admin')
        self.process_index += 1
        p = multiprocessing.Process(
            target=create,
            args=(self.parent.adaptor.name, name, params.instance,
                  msg_factory.instance.get_queue(), loglistener.instance.get_log_desc(), recipient))
        p.start()
        self.processes[name] = p


async def run_wrapper(actor):
    await actor.run()
    tasks = [t for t in asyncio.all_tasks() if not t.done()]
    for t in tasks:
        if t != asyncio.current_task():
            logging.warning(f'There is a pending task: {t}')


def create(lord, name, prms, msg_queue, log_desc, recipient):
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
    performer = admin.Admin(lord, name.host_name, name.process_name, log_desc)
    try:
        actor = adaptor.Adaptor(None, name.get_actor_name(), None, performer, recipient)
        asyncio.run(run_wrapper(actor))
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
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

