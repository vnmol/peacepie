import asyncio
import cProfile
import multiprocessing
import pstats
import sys

import uvloop

from peacepie import PeaceSystem


multiprocessing.set_start_method('spawn', force=True)


async def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    pp = PeaceSystem(sys.argv[1])
    await pp.start()
    try:
        await pp.task
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    # profiler = cProfile.Profile()
    # profiler.enable()
    asyncio.run(main())
    # profiler.disable()
    # stats = pstats.Stats(profiler)
    # stats.sort_stats(pstats.SortKey.CUMULATIVE)
    # stats.print_stats()
