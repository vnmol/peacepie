import logging
import multiprocessing

from peacepie.assist import log_util

instance = None


def init_multimanager(name):
    global instance
    instance = MultiManager(name)


class MultiManager:

    def __init__(self, name):
        self.logger = logging.getLogger()
        self.name = name
        self.manager = multiprocessing.Manager()
        self.logger.info(f'{log_util.get_alias(self)} is created')

    def get_queue(self):
        return self.manager.Queue()
