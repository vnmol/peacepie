import cProfile
import logging
import multiprocessing
import pstats

from peacepie import PeaceSystem

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    logging.info('App is starting ...')
    # profiler = cProfile.Profile()
    # profiler.enable()
    PeaceSystem().start()
    # profiler.disable()
    # stats = pstats.Stats(profiler)
    # stats.sort_stats(pstats.SortKey.CUMULATIVE)
    # stats.print_stats()
    logging.info('App is stopped')
