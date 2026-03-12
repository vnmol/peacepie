# core/config.py
import logging

from core import zmq_client

settings = None


def init():
    global settings
    settings = Settings()
    msg = {'command': 'get_params'}
    ans = zmq_client.client.ask(msg)
    try:
        for param in ans.get('body').get('params'):
            name = param.get('name')
            value = param.get('value')
            if name == 'page_size':
                settings.PAGE_SIZE = value
    except Exception as e:
        logging.exception(e)


class Settings:
    SECRET_KEY: str = "replace-this-with-very-long-random-string-2025!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    PAGE_SIZE = 5



