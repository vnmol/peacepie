import json
import logging
import os

from fastapi import APIRouter, Depends, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from fastapi.templating import Jinja2Templates

from api import html_addons
from core import config, security, zmq_client


router = APIRouter()
templates = Jinja2Templates(directory="templates")


class ContextHolder:

    def __init__(self):
        self.page_size = config.settings.PAGE_SIZE
        self.domain = None
        self.host = None
        self.port = None
        self.sockets = []


context: ContextHolder | None = None


def get_context():
    global context
    if context is None:
        context = ContextHolder()
    return context


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logging.info(f'Websocket({id(websocket)}) is connecting')
    await websocket.accept()
    user = security.get_current_user_from_token(websocket.cookies.get("access_token"))
    if not user:
        await websocket.send_text('User is unknown. Websocket is closed.')
        await websocket.close()
        logging.info(f'Websocket({id(websocket)}) User is unknown')
        logging.info(f'Websocket({id(websocket)}) is closed')
        return
    contxt = get_context()
    contxt.sockets.append(websocket)
    logging.info(f'Websocket({id(websocket)}) ready')
    try:
        while True:
            data = await websocket.receive_text()
            logging.debug(f"Received from websocket({id(websocket)}): '{data}'")
            await websocket_handle(websocket, data)
    except WebSocketDisconnect:
        logging.info(f'Websocket({id(websocket)}) is disconnected')
    except Exception as e:
        logging.exception(e)
    context.sockets.remove(websocket)
    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.close()
    logging.info(f'Websocket({id(websocket)}) is closed')


async def websocket_handle(ws, data):
    ans = zmq_client.client.ask(json.loads(data))
    if isinstance(ans, dict):
        ans = json.dumps(ans)
    await ws.send_text(ans)
    logging.info(f"Sent to websocket({id(ws)}): '{ans}'")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(security.get_current_user)):
    content = await get_content(request)
    return templates.TemplateResponse("actors.html", {"request": request, "user": user, "content": content})


async def get_content(request: Request):
    contxt = get_context()
    if contxt.domain is None:
        contxt.domain = request.headers.get('Host')
        if contxt.domain is None:
            contxt.domain = os.environ.get('DOMAIN', f'{contxt.host}:{contxt.port}')
    param_level = request.query_params.get('level')
    param_recipient = request.query_params.get('recipient')
    param_id = request.query_params.get('id')
    body = {'page_size': contxt.page_size, 'level': param_level, 'recipient': param_recipient, 'id': param_id}
    msg = {'command': 'get_members', 'body': body, 'recipient': param_recipient}
    ans = zmq_client.client.ask(msg)
    body = ans.get('body')
    text = '<div class="menu-grid">\n'
    text += level(body)
    if body.get('_back'):
        text += back(body)
    text += members(body)
    if body.get('nav'):
        text += nav(body)
    text += '<script>\n'
    text += html_addons.script_common
    text += '</script>\n'
    text += '</div>\n'
    if body.get('level') == 'actor':
        text += comm(body)
        text += '<script>\n'
        text += script_command(contxt.domain)
        text += '</script>\n'
    return text


def level(body):
    lvl = body.get('level').upper()
    res = f'<a class="inert_entity">{lvl}</a>\n'
    return res

def back(body):
    bck = body.get('_back')
    res = f'<a class="entity" id="{bck.get("id")}"'
    res += f' data-next_level="{bck.get("next_level")}" data-recipient="{bck.get("recipient")}"'
    res += f'>..</a>\n'
    return res


def members(body):
    res = ''
    for member in body.get('members'):
        clss = 'inert_entity' if not member.get('next_level') else 'entity'
        res += f'<a class="{clss}" id="{member.get("id")}"'
        res += f' data-next_level="{member.get("next_level")}" data-recipient="{member.get("recipient")}"'
        res += f'>{member.get("id")}</a>\n'
    return res


def nav(body):
    nv = body.get('nav')
    count = nv.get('count')
    page = nv.get('page')
    res = '<br><div class="container">\n'
    if page > 0:
        res += f'<a class="entity nav" id="_page_{page - 1}"'
        res += f' data-next_level="{nv.get("next_level")}" data-recipient="{nv.get("recipient")}"'
        res += '><</a>\n'
    res += f'<a id="page" class="page">{page + 1}</a>\n'
    if page < count - 1:
        res += f'<a class="entity nav" id="_page_{page + 1}"'
        res += f' data-next_level="{nv.get("next_level")}" data-recipient="{nv.get("recipient")}"'
        res += '>></a>\n'
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
    res += 'const route = "/actors/ws";\n'
    res += 'webSocket = new WebSocket(protocol + domain + route);'
    res += html_addons.script_websocket
    return res
