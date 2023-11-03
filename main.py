import logging
import multiprocessing
import cProfile
import pstats

import routine_params
import log_conf
from peacepie import PeaceSystem

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    prms = routine_params.get_parameters()
    log_conf.logger_start(prms.get('log_config'))
    logger = logging.getLogger()
    logger.info('App is starting ...')
    profiler = cProfile.Profile()
    profiler.enable()
    PeaceSystem(prms).start()
    profiler.disable()
    profiler.dump_stats('example.stats')
    stats = pstats.Stats('example.stats')
    # stats.print_stats()
    logger.info('App is stopped')
