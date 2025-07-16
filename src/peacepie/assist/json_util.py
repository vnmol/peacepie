import logging

import json as default_json


local_json = default_json


def init(json_package):
    global local_json
    if json_package:
        local_json = json_package


def json_loads(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = local_json.loads(jsn)
    except Exception as ex:
        logging.exception(ex, )
        logging.warning(f'The original string is "{jsn}"')
    return res


def json_dumps(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = local_json.dumps(jsn)
    except Exception as ex:
        logging.exception(ex)
    return res
