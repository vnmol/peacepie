import logging
from pathlib import Path
from fastapi import Depends, Request, APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from core import security, zmq_client


router = APIRouter()
templates = Jinja2Templates(directory="templates")


BASE_DIR = None


def get_base_dir():
    msg = {'command': 'get_base_dir', 'body': None, 'recipient': None}
    ans = zmq_client.client.ask(msg)
    body = ans.get('body') if ans and ans.get('body') else {}
    return Path(body.get('path'))


def secure_path(path: str) -> Path:
    global BASE_DIR
    if BASE_DIR is None:
        try:
            BASE_DIR = get_base_dir()
        except Exception as e:
            logging.exception(e)
    if BASE_DIR is None:
        BASE_DIR = Path.cwd()
    full_path = (BASE_DIR / path).resolve()
    if not str(full_path).startswith(str(BASE_DIR.resolve())):
        raise HTTPException(403, "Доступ запрещён")
    return full_path


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(security.get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return templates.TemplateResponse("files.html", {"request": request, "user": user})


@router.get("/list")
async def list_files(
    path: str = Query(""),
    user=Depends(security.get_current_user)
):
    """
    Возвращает список файлов и папок в указанной папке.
    Пункт ".." НЕ добавляется — переход вверх делается через путь в шапке.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    dir_path = secure_path(path)

    if not dir_path.is_dir():
        raise HTTPException(404, "Папка не найдена")

    items = []

    # Сортировка: сначала папки, потом файлы; внутри — по имени
    for entry in sorted(
        dir_path.iterdir(),
        key=lambda e: (not e.is_dir(), e.name.lower())
    ):
        # Скрываем скрытые файлы/папки (начинающиеся с точки)
        if entry.name.startswith("."):
            continue

        stat = entry.stat()
        is_symlink = entry.is_symlink()
        target = entry.resolve() if is_symlink else None

        item = {
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "is_symlink": is_symlink,
            "target": str(target) if is_symlink and target else None,
        }
        items.append(item)

    return items


@router.get("/file-content")
async def get_file_content(
    path: str = Query(...),
    user=Depends(security.get_current_user)
):
    """
    Возвращает содержимое текстового файла для просмотра в модальном окне.
    Ограничение — не более 2 МБ.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    file_path = secure_path(path)

    if not file_path.is_file():
        raise HTTPException(404, "Файл не найден")

    if file_path.stat().st_size > 2 * 1024 * 1024:  # 2 МБ
        raise HTTPException(413, "Файл слишком большой для просмотра")

    def iterfile():
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="text/plain; charset=utf-8"
    )