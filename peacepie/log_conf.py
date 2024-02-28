import os

import json
import logging
import logging.config
import sys
from logging.handlers import RotatingFileHandler

from peacepie import params
from peacepie.assist import dir_operations

LOG_PATH = 'logs/log.log'

logger = None
# logger_listener = None
# log_desc = None


def logger_start(config_filename):
    global logger
    # global logger_listener
    # global log_desc
    if logger:
        return
    try:
        with open(config_filename) as f:
            config = json.load(f)
        check_paths(config)
        logging.config.dictConfig(config)
        logger = logging.getLogger()
        logger.info('Logging.config is set from: ' + config_filename)
    except BaseException as ex:
        logger = get_default_logger()
        logger.exception(ex)


def get_default_logger():
    handler = RotatingFileHandler(
        filename=LOG_PATH, mode='a', maxBytes=10485760, backupCount=5)
    formatter = logging.Formatter('%(levelname)-7s %(asctime)s %(processName)-11s %(lineno)4d %(module)-15s : %(message)s')
    handler.setFormatter(formatter)
    res = logging.getLogger()
    res.setLevel('DEBUG')
    res.addHandler(handler)
    res.info('Default logger is created')
    return res


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
