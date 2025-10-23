import asyncio
import logging
import os

from aiohttp import web, WSMsgType

from simple_web_face import file_browser_handler, html_addons


class SimpleWebFace:

    def __init__(self):
        self.adaptor = None
        self.page_size = 5
        self.http_port = None
        self._http_host = None
        self._domain = None
        self._runner = None
        self._sockets = []
        self.file_browser = None

    async def pre_run(self):
        browser_base_dir = self.adaptor.get_param('browser_base_dir')
        self.file_browser = file_browser_handler.FileBrowserHandler(browser_base_dir=browser_base_dir)

    async def exit(self):
        await self.close_websockets()
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        logging.info(f'HTTP server stopped at http://{self._http_host}:{self.http_port}')

    async def close_websockets(self, timeout=1):
        for ws in self._sockets:
            if ws.closed:
                continue
            ws_id = id(ws)
            try:
               await asyncio.wait_for(ws.close(), timeout=timeout)
            except asyncio.TimeoutError:
                if not ws.closed:
                    ws._writer.transport.close()
                    logging.info(f'Websocket({ws_id}) is force closed')
        self._sockets.clear()

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        self._http_host = '0.0.0.0'
        self._runner = await self.initialize_http_server()
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))

    async def initialize_http_server(self):
        self.http_port = int(os.environ.get('PORT', self.http_port))
        app = web.Application()
        app.add_routes([web.get('/', self.root_handler)])
        app.add_routes([web.get('/ws', self.websocket_handler)])
        app.add_routes([web.get('/favicon.ico', favicon)])
        app.add_routes([web.get('/browse', self.file_browser.handle_browse)])
        _runner = web.AppRunner(app)
        await _runner.setup()
        site = web.TCPSite(_runner, f'{self._http_host}', self.http_port)
        await site.start()
        logging.info(f'HTTP server started at http://{self._http_host}:{self.http_port}')
        return _runner

    async def root_handler(self, request):
        if self._domain is None:
            self._domain = request.headers.get('Host')
            if self._domain is None:
                self._domain = os.environ.get('DOMAIN', f'{self._http_host}:{self.http_port}')
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
        text += level(body)
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
            text += script_command(self._domain)
        text += '</script>\n</body>\n</html>'
        return web.Response(text=text, content_type='text/html')

    async def websocket_handler(self, request):
        logging.info('Websocket connection starting')
        ws = web.WebSocketResponse()
        self._sockets.append(ws)
        await ws.prepare(request)
        logging.info(f'Websocket({id(ws)}) ready')
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                logging.debug(f"Received from websocket({id(ws)}): '{msg.data}'")
                try:
                    await self.websocket_handle(ws, msg.data)
                except Exception as e:
                    logging.exception(e)
        self._sockets.remove(ws)
        logging.info(f'Websocket({id(ws)}) is closed')
        return ws

    async def websocket_handle(self, ws, data):
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
        await ws.send_str(res)
        logging.info(f"Sent to websocket({id(ws)}): '{res}'")


async def favicon(request):
    return web.FileResponse(f'{os.path.dirname(__file__)}/resources/favicon.ico')

def level(body):
    lvl = body.get('level').upper()
    res = f'<button class="last_entity">{lvl}</button>\n<br><br>\n'
    return res

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


def script_command(domain):
    res = 'const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";\n'
    res += f'const domain = "{domain}";\n'
    res += 'const route = "/ws";\n'
    res += 'webSocket = new WebSocket(protocol + domain + route);'
    res += html_addons.script_websocket
    return res
