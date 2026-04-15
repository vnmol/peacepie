import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import config, security, zmq_client
from api import actors, auth, files, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    zmq_client.init()
    config.init()
    yield


app = FastAPI(lifespan=lifespan)


app.mount("/static", StaticFiles(directory="templates/static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.cache = None


app.include_router(auth.router, prefix='/auth')
app.include_router(files.router, prefix='/files', tags=["files"])
app.include_router(actors.router, prefix='/actors', tags=["actors"])
app.include_router(users.router, prefix='/users', tags=["users"])


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join("templates", "static", "favicon.ico")
    return FileResponse(
        favicon_path,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(security.get_current_user)):
    error_message = request.cookies.get("error_message")
    if isinstance(error_message, dict):
        error_message = str(error_message)
    response = templates.TemplateResponse("index.html", {"request": request, "error_message": error_message, "user": user})
    response.delete_cookie("error_message")
    return response
