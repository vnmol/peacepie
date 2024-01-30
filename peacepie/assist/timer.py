import asyncio
import traceback

from peacepie import msg_factory


def start(queue, mid, timeout=1):
    asyncio.get_running_loop().create_task(wait(queue, mid, timeout))


async def wait(queue, mid, timeout):
    if not timeout:
        print(mid, timeout)
    await asyncio.sleep(timeout)
    body = {'mid': mid}
    await queue.put(msg_factory.get_msg('timeout', body))

