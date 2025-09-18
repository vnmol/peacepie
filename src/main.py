import asyncio
import multiprocessing
import sys
from datetime import datetime

import uvloop
import ujson

from peacepie import PeaceSystem


multiprocessing.set_start_method('spawn', force=True)


async def main():
    # print(datetime.now().strftime("%H:%M:%S.%f"))
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    param = sys.argv[1] if len(sys.argv) > 1 else None
    pp = PeaceSystem(param, json_package=ujson)
    await pp.start()
    try:
        await pp.task
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    asyncio.run(main())
