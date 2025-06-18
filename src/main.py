import asyncio
import multiprocessing
import sys

import uvloop

from peacepie import PeaceSystem

multiprocessing.set_start_method('spawn', force=True)


async def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    param = sys.argv[1] if len(sys.argv) > 1 else None
    pp = PeaceSystem(param)
    await pp.start()
    try:
        await pp.task
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    asyncio.run(main())
