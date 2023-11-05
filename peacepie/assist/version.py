VERSION = 'version'
MAJOR_LEVEL = 'major'
MINOR_LEVEL = 'minor'
MICRO_LEVEL = 'micro'
VERSION_LEVELS = (MAJOR_LEVEL, MINOR_LEVEL, MICRO_LEVEL)


def to_string(val):
    return f'{val[MAJOR_LEVEL]}.{val[MINOR_LEVEL]}.{val[MICRO_LEVEL]}'


def from_string(val):
    lst = val.split('.')
    if len(lst) == 0:
        return None
    while len(lst) < 3:
        lst.append('0')
    if not all(val.isnumeric() for val in lst):
        return None
    res = {MAJOR_LEVEL: int(lst[0]), MINOR_LEVEL: int(lst[1]), MICRO_LEVEL: int(lst[2])}
    return res


def find_max_version(actor, lst, conditions):
    res = None
    for ver in lst:
        if check_version(actor, ver, conditions):
            if res is None:
                res = ver
            elif check_version(ver, {'>': res}):
                res = ver
    return res


def check_version(actor, ver, conditions):
    try:
        return _check_version(ver, conditions)
    except Exception as ex:
        actor.logger.exception(ex)
        return False


def _check_version(version, conditions):
    if not version:
        return False
    if not conditions:
        return True
    for (condition, value) in conditions.items():
        if condition == '==':
            for level in VERSION_LEVELS:
                if version[level] != value[level]:
                    return False
        elif condition == '>':
            failure = True
            for level in VERSION_LEVELS:
                if version[level] > value[level]:
                    failure = False
                    break
                elif version[level] < value[level]:
                    return False
            if failure:
                return False
        elif condition == '<':
            failure = True
            for level in VERSION_LEVELS:
                if version[level] < value[level]:
                    failure = False
                    break
                elif version[level] > value[level]:
                    return False
            if failure:
                return False
        elif condition == '>=':
            for level in VERSION_LEVELS:
                if version[level] > value[level]:
                    break
                elif version[level] < value[level]:
                    return False
        elif condition == '<=':
            for level in VERSION_LEVELS:
                if version[level] < value[level]:
                    break
                elif version[level] > value[level]:
                    return False
        else:
            return False
    return True


def conditions_as_text(conditions):
    res = ''
    if conditions:
        for (condition, val) in conditions.items():
            res += f'{condition}{to_string(val)}'
    return res
