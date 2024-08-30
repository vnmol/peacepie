import logging

import ujson as json


def json_loads(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = json.loads(jsn)
    except Exception as ex:
        logging.exception(ex)
        logging.warning(f'The original string is "{jsn}"')
    return res


def json_dumps(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = json.dumps(jsn)
    except Exception as ex:
        logging.exception(ex)
    return res
