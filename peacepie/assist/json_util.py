import json
import logging

logger = logging.getLogger()


def json_loads(jsn):
    res = None
    try:
        res = json.loads(jsn)
    except Exception as ex:
        logger.exception(ex)
    return res


def json_dumps(jsn):
    res = None
    try:
        res = json.dumps(jsn)
    except Exception as ex:
        logger.exception(ex)
    return res
