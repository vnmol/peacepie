import asyncio
import threading


def thread_function(sync_function, sync_args, loop, result_future):
    try:
        result = sync_function(sync_args)
    except Exception as e:
        loop.call_soon_threadsafe(result_future.set_exception, e)
    else:
        loop.call_soon_threadsafe(result_future.set_result, result)


async def sync_as_async(sync_function, sync_args):
    loop = asyncio.get_event_loop()
    result_future = loop.create_future()
    thread = threading.Thread(target=thread_function, args=(sync_function, sync_args, loop, result_future))
    thread.start()
    result = await result_future
    return result
