import logging
import os
from aiohttp import web, WSMsgType

from peacepie_example import html_addons


class SimpleWebFace:

    def __init__(self):
        self.adaptor = None
        self.page_size = 5
        self.http_host = None
        self.http_port = None
        self.runner = None
        self.sockets = []

    async def exit(self):
        for ws in self.sockets:
            await ws.close()
            logging.info(f'Websocket({id(ws)}) closed')
        await self.runner.cleanup()
        logging.info(f'HTTP server stopped at http://localhost:{self.http_port}')

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'start':
            await self.start(msg)
        elif command == 'is_ready_to_move':
            await self.is_ready_to_move(sender)
        elif command == 'move':
            await self.move(body, sender)
        else:
            return False
        return True

    async def is_ready_to_move(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('ready', None, recipient))

    async def move(self, clone_addr, recipient):
        await self.adaptor.ask(self.adaptor.get_control_msg('start', {'port': self.http_port}, clone_addr), 10)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('moved', None, recipient))

    async def start(self, msg):
        self.http_host = self.adaptor.get_param('ip')
        self.http_port = msg.get('body').get('port') if msg.get('body') else None
        self.runner = await self.initialize_http_server()
        recipient = msg.get('sender')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))

    async def initialize_http_server(self):
        app = web.Application()
        app.add_routes([web.get('/', self.root_handler)])
        app.add_routes([web.get('/ws', self.websocket_handler)])
        app.add_routes([web.get('/favicon.ico', favicon)])
        app.add_routes([web.get('/logs', logs_handler)])
        app.add_routes([web.get('/logs/{path:.*}', logs_handler)])
        app.add_routes([web.get('/log_view', log_view_handler)])
        app.add_routes([web.get('/log_view/{path:.*}', log_view_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.http_port)
        await site.start()
        logging.info(f'HTTP server started at http://localhost:{self.http_port}')
        return runner

    async def root_handler(self, request):
        param_level = request.query.get('level')
        param_recipient = request.query.get('recipient')
        if not param_recipient:
            param_recipient = self.adaptor.get_head_addr()
        param_id = request.query.get('id')
        body = {'page_size': self.page_size, 'level': param_level, 'recipient': param_recipient, 'id': param_id}
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_members', body, param_recipient))
        head = f'<head>\n<meta charset="UTF-8">\n<style>\n{html_addons.entity_style}\n</style>\n</head>\n\n'
        text = f'<!DOCTYPE html>\n<html>\n{head}<body>\n\n'
        body = ans.get('body')
        if body.get('_back'):
            text += back(body)
        text += members(body)
        if body.get('nav'):
            text += nav(body)
        if body.get('level') == 'actor':
            text += comm(body)
        text += '<script>\n'
        text += html_addons.script_common
        if body.get('level') == 'actor':
            text += script_command(self.http_host, self.http_port)
        text += '</script>\n</body>\n</html>'
        return web.Response(text=text, content_type='text/html')

    async def websocket_handler(self, request):
        logging.info('Websocket connection starting')
        ws = web.WebSocketResponse()
        self.sockets.append(ws)
        await ws.prepare(request)
        logging.info(f'Websocket({id(ws)}) ready')
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                logging.debug(f'Received from websocket({id(ws)}): {msg.data}')
                res = await self.websocket_handle(msg.data)
                await ws.send_str(res)
                logging.debug(f'Sent to websocket({id(ws)}): {res}')
        self.sockets.remove(ws)
        logging.info(f'Websocket({id(ws)}) closed')
        return ws

    async def websocket_handle(self, data):
        datum = self.adaptor.json_loads(data)
        tp = datum.get('type')
        command = datum.get('command')
        body = datum.get('body')
        timeout = 4
        try:
            timeout = int(datum.get('timeout'))
        except ValueError as e:
            logging.exception(e)
        recipient = datum.get('recipient')
        if recipient == '':
            recipient = None
        query = self.adaptor.get_msg(command, body, recipient)
        if tp == 'ask':
            res = self.adaptor.json_dumps(await self.adaptor.ask(query, timeout))
        else:
            await self.adaptor.send(query)
            res = 'The message is sent'
        return res


async def favicon(request):
    return web.FileResponse(f'{os.path.dirname(__file__)}/resources/favicon.ico')


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


def comm(body):
    recipient = body.get('members')[0].get('id')
    res = html_addons.script_command_begin
    res += f'  <input type="text" id="recipient" name="recipient" value="{recipient}">\n'
    res += html_addons.script_command_end
    return res


def script_command(host, port):
    res = f'webSocket = new WebSocket("ws://{host}:{port}/ws");'
    res += 'window.addEventListener("beforeunload", function() { socket.close(); });'
    res += html_addons.script_websocket
    return res


async def logs_handler(request):
    path = request.match_info.get('path', '')
    print('logs', path)
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


async def log_view_handler(request):
    path = request.match_info.get('path', '')
    if not path.startswith('/'):
        path = '/' + path
    if path.endswith('/'):
        path = path[:-1]
    view_path = f'/log_view{path}'
    logs_path = f'/logs{path}'
    logs_dir = '.' + logs_path
    if not os.path.exists(logs_dir):
        return web.Response(text=f'Путь "{logs_dir}" не найден', status=404)
    if os.path.isfile(logs_dir):
        with open(logs_dir, 'rb') as f:
            content = f.read()
        return web.Response(body=content, content_type='text/plain', headers={'Content-Disposition': 'inline'})
    content = ''
    if path:
        parent_path = os.path.dirname(logs_path).replace('/logs', '/log_view')
        content += f"<a href='{parent_path}'>..</a><br>"
    items = [(item, os.path.isdir(os.path.join(logs_dir, item))) for item in os.listdir(logs_dir)]
    foldernames = [item[0] for item in items if item[1]]
    foldernames.sort()
    filenames = [item[0] for item in items if not item[1]]
    filenames.sort()
    for foldername in foldernames:
        content += f"<a href='{view_path}/{foldername}/'>{foldername}/</a><br>"
    for filename in filenames:
        content += f"<a href='{view_path}/{filename}'>{filename}</a><br>"
    return web.Response(text=content, content_type='text/html')
