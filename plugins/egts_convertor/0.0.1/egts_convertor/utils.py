from datetime import datetime, timezone

from egts_convertor import constants


def get_now():
    return int(datetime.now(tz=timezone.utc).timestamp()) - constants.DEFAULT_BEGIN_TIME
