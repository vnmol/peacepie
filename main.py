import logging
import multiprocessing

from peacepie import PeaceSystem

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    # log_conf.logger_start(prms.get('log_config'))
    logger = logging.getLogger()
    logger.info('App is starting ...')
    # profiler = cProfile.Profile()
    # profiler.enable()
    PeaceSystem().start()
    # profiler.disable()
    # profiler.dump_stats('example.stats')
    # stats = pstats.Stats('example.stats')
    # stats.print_stats()
    logger.info('App is stopped')
