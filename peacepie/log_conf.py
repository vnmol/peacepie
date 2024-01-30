import os

import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler

from peacepie import params
from peacepie.assist import dir_operations

LOG_PATH = 'logs/log.log'

logger = None
logger_listener = None

log_desc = None


def logger_start(config_filename):
    global logger
    global logger_listener
    global log_desc
    if logger:
        return
    try:
        with open(config_filename) as f:
            config = json.load(f)
        if params.instance.get('developing_mode'):
            filenames = set([handler.get('filename') for handler in config.get('handlers').values()])
            for filename in filenames:
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    pass
        logging.config.dictConfig(config)
        logger = logging.getLogger()
    except BaseException as ex:
        logger = get_default_logger()
        logger.exception(ex)
    logger.info('Logging.config is defined')


def get_default_logger():
    handler = RotatingFileHandler(
        filename=LOG_PATH, mode='a', maxBytes=10485760, backupCount=5)
    formatter = logging.Formatter('%(levelname)-7s %(asctime)s %(processName)-11s %(lineno)4d %(module)-15s : %(message)s')
    handler.setFormatter(formatter)
    res = logging.getLogger()
    res.setLevel('DEBUG')
    res.addHandler(handler)
    return res
