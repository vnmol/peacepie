import logging

import json as default_json

serializer = default_json


def init():
    try:
        import ujson as external
    except Exception as e:
        logging.exception(e)
        return
    global serializer
    serializer = external


def json_loads(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = serializer.loads(jsn)
    except Exception as ex:
        logging.exception(ex, )
        logging.warning(f'The original string is "{jsn}"')
    return res


def normalize_key(key):
    if isinstance(key, (int, tuple)):
        return str(key)
    return key

def normalize(obj):
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {normalize_key(key): normalize(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [normalize(item) for item in obj]
    elif isinstance(obj, tuple):
        return list(normalize(item) for item in obj)
    else:
        return obj


def json_dumps(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = serializer.dumps(jsn)
        return res
    except TypeError:
        pass
    except Exception as e:
        logging.exception(e)
        return None
    try:
        res = serializer.dumps(normalize(jsn))
    except Exception as e:
        logging.exception(e)
    return res
