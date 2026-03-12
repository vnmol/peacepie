import json

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core import config, security, zmq_client
from api.emulator import emulator

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(security.get_current_user)):
    return templates.TemplateResponse("roles.html", {"request": request, "user": user})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    need_to_close = True
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(message)

            # Отправляем сообщение эмулятору
            response = emulator.ask(message)
            print(response)

            # Отправляем ответ клиенту
            await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        need_to_close = False
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if need_to_close:
            await websocket.close()
