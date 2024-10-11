import asyncio

from peacepie import msg_factory


def start(timeout, queue, mid=None):
    asyncio.get_running_loop().create_task(wait(timeout, queue, mid))


async def wait(timeout, queue, mid):
    await asyncio.sleep(timeout)
    await queue.put(msg_factory.get_msg('timer', {'mid': mid}))

