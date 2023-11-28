import asyncio
import logging
from logging.handlers import QueueHandler

from aiohttp import web
from aiohttp.web_runner import GracefulExit

from simple_web_face import client_link


logger = None

CLIENT_LINK = None


def create(log_desc, http_port, link_host, link_port, seralizer):
    global logger
    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])
    logger.addHandler(QueueHandler(log_desc.queue))
    logger.setLevel(log_desc.level)
    logger.info(f'HttpServer on port {http_port} is started')
    app = web.Application()
    app.add_routes([web.get('/', root_handler)])
    try:
        asyncio.run(run(app, http_port, link_host, link_port, seralizer))
    except GracefulExit as ex:
        pass


async def run(app, http_port, link_host, link_port, serializer):
    await asyncio.gather(
        asyncio.create_task(web._run_app(app, port=http_port)),
        asyncio.create_task(init_client(link_host, link_port, serializer))
    )


async def init_client(link_host, link_port, serializer):
    global CLIENT_LINK
    CLIENT_LINK = client_link.ClientLink(link_host, link_port, serializer)
    await CLIENT_LINK.start_client()


async def root_handler(request):
    msg = {'command': 'get_processes'}
    ans = await CLIENT_LINK.ask(msg)
    res = ''
    if ans:
        for name in ans.get('list'):
            res += '<option value="' + name + '">' + name + '</option>'
    text = '<!DOCTYPE html><html><head><style>.scrollable-list {padding: 5px;}option{padding:20px;}</style>PEACEPIE</head><body><div class="scrollable-list"><select name="Processes" size="6">'
    text += res
    text += '</select></div></body></html>'
    return web.Response(
        text=text,
        content_type='text/html'
    )
