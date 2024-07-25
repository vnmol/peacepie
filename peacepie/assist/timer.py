import asyncio

from peacepie import msg_factory


def start(queue, mid, timeout=1):
    asyncio.get_running_loop().create_task(wait(queue, mid, timeout))


async def wait(queue, mid, timeout):
    await asyncio.sleep(timeout)
    await queue.put(msg_factory.get_msg('timeout', {'mid': mid}))

