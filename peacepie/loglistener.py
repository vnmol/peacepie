import logging
import os

from peacepie.assist import log_util, dir_operations
from peacepie import multimanager

LOG_PATH = './logs/log.log'

instance = None


def init_loglistener(name):
    global instance
    instance = LogListener(name)


class LogListener:

    def __init__(self, name):
        self.logger = logging.getLogger()
        self.name = name
        queue = multimanager.instance.get_queue()
        if len(self.logger.handlers) == 0:
            add_default_handler(self.logger)
        handler = self.logger.handlers[0]
        self.log_desc = LogDesc(queue, handler.level)
        self.logger_listener = logging.handlers.QueueListener(queue, handler)
        self.logger_listener.start()
        self.logger.info(f'{log_util.get_alias(self)} is created')

    def get_log_desc(self):
        return self.log_desc

    def stop(self):
        self.logger_listener.stop()
        self.logger.info(f'{log_util.get_alias(self)} is stopped')


def add_default_handler(logger):
    dir_operations.makedir(os.path.dirname(LOG_PATH))
    handler = logging.handlers.RotatingFileHandler(
        filename=LOG_PATH, mode='a', maxBytes=10485760, backupCount=5)
    formatter = logging.Formatter('%(levelname)-7s %(asctime)s %(processName)-11s %(lineno)4d %(module)-15s : %(message)s')
    handler.setFormatter(formatter)
    logger.setLevel('DEBUG')
    logger.addHandler(handler)


class LogDesc:

    def __init__(self, queue, level):
        self.queue = queue
        self.level = level

    def __repr__(self):
        res = f'{self.__class__.__name__}(queue={self.queue}, level={logging.getLevelName(self.level)})'
        return res
