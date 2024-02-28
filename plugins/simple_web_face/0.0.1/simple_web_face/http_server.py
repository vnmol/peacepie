import asyncio
import logging
import os
from logging.handlers import QueueHandler

from aiohttp import web, WSMsgType
from aiohttp.web_runner import GracefulExit

from simple_web_face import client_link, html_addons


class HttpServer:

    def __init__(self):
        self.logger = None
        self.page_size = 5
        self.http_host = None
        self.http_port = None
        self.app = None
        self.client_link = None

    def init(self, log_desc, link_host, link_port, serializer, http_host, http_port):
        self.logger = logging.getLogger()
        while self.logger.hasHandlers():
            self.logger.removeHandler(self.logger.handlers[0])
        self.logger.addHandler(QueueHandler(log_desc.queue))
        self.logger.setLevel(log_desc.level)
        self.http_host = http_host
        self.http_port = http_port
        self.app = web.Application()
        self.app.add_routes([web.get('/', root_handler)])
        self.app.add_routes([web.get('/favicon.ico', favicon)])
        self.app.add_routes([web.get('/ws', websocket_handler)])
        self.app.add_routes([web.get('/logs', logs_handler)])
        self.app.add_routes([web.get('/logs/{path:.*}', logs_handler)])
        self.client_link = client_link.ClientLink(link_host, link_port, serializer)


instance = HttpServer()


def create(log_desc, host, link_port, serializer, http_host, http_port):
    instance.init(log_desc, host, link_port, serializer, http_host, http_port)
    logging.info(f'HttpServer on port {http_port} is started')
    try:
        asyncio.run(run())
    except GracefulExit as ex:
        pass


async def run():
    await asyncio.gather(
        asyncio.create_task(web._run_app(instance.app, port=instance.http_port)),
        asyncio.create_task(instance.client_link.start_client())
    )


async def favicon(request):
    return web.FileResponse(f'{os.path.dirname(__file__)}/resources/favicon.ico')


async def root_handler(request):
    param_level = request.query.get('level')
    param_recipient = request.query.get('recipient')
    param_id = request.query.get('id')
    body = {'page_size': instance.page_size, 'level': param_level, 'recipient': param_recipient, 'id': param_id}
    ans = await instance.client_link.ask({'command': 'get_members', 'body': body})
    text = f'<!DOCTYPE html>\n<html>\n<head>\n<style>\n{html_addons.entity_style}\n</style>\n</head>\n\n<body>\n\n'
    body = ans.get('body')
    if body.get('_back'):
        text += back(body)
    text += members(body)
    if body.get('nav'):
        text += nav(body)
    if body.get('level') == 'actor':
        text += command(body)
    text += '<script>\n'
    text += html_addons.script_common
    if body.get('level') == 'actor':
        text += script_command()
    text += '</script>\n</body>\n</html>'
    return web.Response(text=text, content_type='text/html')


def back(body):
    bck = body.get('_back')
    res = f'<button class="entity" id="{bck.get("id")}"'
    res += f' data-next_level="{bck.get("next_level")}" data-recipient="{bck.get("recipient")}"'
    res += f'>..</button>\n<br><br>\n'
    return res


def members(body):
    res = ''
    for member in body.get('members'):
        clss = 'last_entity' if not member.get('next_level') else 'entity'
        res += f'<button class="{clss}" id="{member.get("id")}"'
        res += f' data-next_level="{member.get("next_level")}" data-recipient="{member.get("recipient")}"'
        res += f'>{member.get("id")}</button>\n'
    return res


def nav(body):
    nv = body.get('nav')
    count = nv.get('count')
    page = nv.get('page')
    res = '<br><br><br><div class="container">\n'
    if page > 0:
        res += f'<button class="entity nav" id="_page_{page - 1}"'
        res += f' data-next_level="{nv.get("next_level")}" data-recipient="{nv.get("recipient")}"'
        res += '><</button>\n'
    res += f'<button id="page" class="page">{page + 1}</button>\n'
    if page < count - 1:
        res += f'<button class="entity nav" id="_page_{page + 1}"'
        res += f' data-next_level="{nv.get("next_level")}" data-recipient="{nv.get("recipient")}"'
        res += '>></button>\n'
    res += '</div>\n'
    return res


def command(body):
    recipient = body.get('members')[0].get('id')
    res = html_addons.script_command_begin
    res += f'  <input type="text" id="recipient" name="recipient" value="{recipient}">\n'
    res += html_addons.script_command_end
    return res


def script_command():
    res = f'webSocket = new WebSocket("ws://{instance.http_host}:{instance.http_port}/ws");'
    res += html_addons.script_websocket
    return res


async def websocket_handler(request):
    logging.info('Websocket connection starting')
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    logging.info('Websocket connection ready')
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            logging.debug(msg.data)
            if msg.data == 'close':
                await ws.close()
            else:
                res = await websocket_handle(msg.data)
                await ws.send_str(res)
    logging.info('Websocket connection closed')
    return ws


async def websocket_handle(body):
    ans = await instance.client_link.ask({'command': 'websocket_handle', 'body': body})
    if not ans:
        ans = 'No response was received'
    return ans


async def logs_handler(request):
    path = request.match_info.get('path', '')
    logs_path = os.path.join('/logs/', path)
    if logs_path.endswith('/'):
        logs_path = logs_path[:-1]
    logs_dir = '.' + logs_path
    if not os.path.exists(logs_dir):
        return web.Response(text=f'Путь "{logs_dir}" не найден', status=404)
    if os.path.isfile(logs_dir):
        with open(logs_dir, 'rb') as f:
            content = f.read()
        return web.Response(body=content)
    content = ''
    if path:
        parent_path = os.path.dirname(logs_path)
        content += f"<a href='{parent_path}'>..</a><br>"
    items = [(item, os.path.isdir(os.path.join(logs_dir, item))) for item in os.listdir(logs_dir)]
    foldernames = [item[0] for item in items if item[1]]
    foldernames.sort()
    filenames = [item[0] for item in items if not item[1]]
    filenames.sort()
    for foldername in foldernames:
        content += f"<a href='{logs_path}/{foldername}/'>{foldername}/</a><br>"
    for filename in filenames:
        content += f"<a href='{logs_path}/{filename}'>{filename}</a><br>"
    return web.Response(text=content, content_type='text/html')
