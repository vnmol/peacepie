import json
import logging

logger = logging.getLogger()


def json_loads(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = json.loads(jsn)
    except Exception as ex:
        logger.exception(ex)
        logger.warning(f'The original string is "{jsn}"')
    return res


def json_dumps(jsn):
    if not jsn:
        return None
    res = None
    try:
        res = json.dumps(jsn)
    except Exception as ex:
        logger.exception(ex)
    return res
