import asyncio
import logging
import multiprocessing
import subprocess
import sys
from logging.handlers import QueueHandler

from peacepie import msg_factory, params, loglistener
from peacepie.assist import log_util, dir_operations


class PackageLoader:

    def __init__(self, parent):
        self.parent = parent
        self.not_log_commands = set()
        self.cumulative_commands = {}
        self.queue = asyncio.Queue()
        self.path = f'{params.instance.get("package_dir")}/source'
        dir_operations.makedir(self.path)
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self, queue):
        await queue.put(msg_factory.get_msg('ready'))
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

    async def handle(self, msg):
        command = msg['command']
        if command == 'load_package':
            await self.load_package(msg)
        else:
            return False
        return True

    async def load_package(self, msg):
        log_desc = loglistener.instance.get_log_desc()
        url = params.instance.get('extra-index-url')
        body = msg.get('body') if msg.get('body') else {}
        package_name = body.get('package_name')
        recipient = msg.get('sender')
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=load_package, args=(log_desc, url, self.path, package_name, queue,))
        process.start()
        while process.is_alive():
            await asyncio.sleep(1)
        process.join()
        res = queue.get()
        await self.parent.connector.send(self, msg_factory.get_msg(res.get('command'), None, recipient))


def load_package(log_desc, url, path, package_name, queue):
    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])
    logger.addHandler(QueueHandler(log_desc.queue))
    logger.setLevel(log_desc.level)
    res = {}
    code = None
    try:
        host = url.split("//")[-1].split("/")[0]
        args = ([sys.executable, '-m', 'pip', 'download', '--disable-pip-version-check'])
        if url:
            args.append(f'--trusted-host={host}')
            args.append(f'--extra-index-url={url}')
        args.append(f'-d{path}')
        args.append(package_name)
        logging.info(args)
        code = subprocess.check_call(args)
    except Exception as ex:
        logging.exception(ex)
    res['command'] = 'package_is_loaded' if code == 0 else 'package_is_not_loaded'
    queue.put(res)
