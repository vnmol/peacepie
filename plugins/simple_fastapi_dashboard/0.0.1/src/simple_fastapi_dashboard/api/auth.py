# api/auth.py
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core import security


router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = security.authenticate_user(username, password)
    if user is None:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверное имя пользователя или пароль"
        }, status_code=400)
    token = security.create_jwt_token(data={"sub": user.get('username')})
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60*60*24*30,
        expires=60*60*24*30,
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    security.revoke_token(request)
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie("access_token")
    return response
