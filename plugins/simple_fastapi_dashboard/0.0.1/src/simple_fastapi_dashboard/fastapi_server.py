import hashlib
import json
import logging
import logging.config
import multiprocessing
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import uvicorn
from argon2 import PasswordHasher
import jwt

from . import zmq_client

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

class FastapiServer:

    def __init__(self, zmq_port, serializer_spec):
        self.zmq_client = zmq_client.ZMQClient(zmq_port, serializer_spec)
        self.hasher = PasswordHasher()
        hashed_password = self.hasher.hash('secret')
        self.fake_users_db = {
            'admin': {
                'username': 'admin',
                'hashed_password': hashed_password,
            }
        }

    def verify_password(self, hashed_password, password):
        return self.hasher.verify(hashed_password, password)

    def get_password_hash(self, password):
        return self.hasher.hash(password)

    def authenticate_user(self, username, password):
        user = self.fake_users_db.get(username)
        if not user:
            return False
        if not self.verify_password(user.get('hashed_password'), password):
            return False
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

def check_paths(developing_mode, config):
    filenames = set([handler.get('filename') for handler in config.get('handlers').values()])
    filepaths = set([os.path.dirname(filename) for filename in filenames])
    for filepath in filepaths:
        if not os.path.exists(filepath):
            os.makedirs(filepath)
    if developing_mode or 'pycharm' in sys.executable.lower():
        for filename in filenames:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass


def set_log_config(log_config):
    config_filename = log_config.get('config_filename')
    process = f'/{multiprocessing.current_process().name}'
    config = None
    try:
        with open(config_filename) as f:
            config = json.load(f)
        for _, handler_config in config.get('handlers', {}).items():
            if 'filename' in handler_config:
                handler_config['filename'] = f'{log_config.get("log_dir")}{process}/{handler_config["filename"]}'
        check_paths(log_config.get('developing_mode'), config)
        logging.config.dictConfig(config)
    except BaseException as ex:
        logging.exception(ex)
    return config


def run_server(log_config, port, zmq_port, serializer_spec):
    config = set_log_config(log_config)
    server = FastapiServer(zmq_port, serializer_spec)
    app = FastAPI()
    templates = Jinja2Templates(directory=f'{os.path.dirname(__file__)}/resources/templates')

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(f'{os.path.dirname(__file__)}/resources/static/favicon.ico')

    @app.get("/", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse("login.html", {"request": request})

    @app.post("/login")
    async def login(username: str = Form(...), password: str = Form(...)):
        user = server.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = server.create_access_token(data={"sub": user["username"]})
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("access_token", token, httponly=True)
        return response

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=400, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=400, detail="Token expired")
        return templates.TemplateResponse("dashboard.html", {"request": request, "username": username})

    @app.get("/logout")
    async def logout():
        response = RedirectResponse(url="/")
        response.delete_cookie("access_token")
        return response

    uvicorn.run(app, host="0.0.0.0", port=port, log_config=config)
