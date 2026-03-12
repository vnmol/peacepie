import logging

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request

from core import config, zmq_client


revoked_tokens = set()


def get_current_user_from_token(token):
    if token is None or token in revoked_tokens:
        return None
    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        user = {'username': payload.get("sub")}
        return user
    except Exception as e:
        logging.exception(e)
        return None

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    user = get_current_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=302,
            headers={"Location": "/auth/login"}
        )
    return user

def authenticate_user(username, password):
    body = {'username': username, 'password': password}
    msg = {'command': 'authenticate', 'body': body, 'recipient': 'account_admin'}
    ans = zmq_client.client.ask(msg)
    return ans.get('body')

def create_jwt_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)

def revoke_token(request: Request):
    token = request.cookies.get("access_token")
    if token is not None:
        revoked_tokens.add(request.cookies.get("access_token"))
