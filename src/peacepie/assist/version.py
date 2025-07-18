import logging
import re
import html


VERSION = 'version'
MAJOR_LEVEL = 'major'
MINOR_LEVEL = 'minor'
MICRO_LEVEL = 'micro'
VERSION_LEVELS = (MAJOR_LEVEL, MINOR_LEVEL, MICRO_LEVEL)


def version_to_string(val):
    return f'{val[MAJOR_LEVEL]}.{val[MINOR_LEVEL]}.{val[MICRO_LEVEL]}'


def version_from_string(val):
    if not val:
        return None
    lst = val.split('.')
    if len(lst) == 0:
        return None
    while len(lst) < 3:
        lst.append('0')
    if not all(val.isnumeric() for val in lst):
        return None
    res = {MAJOR_LEVEL: int(lst[0]), MINOR_LEVEL: int(lst[1]), MICRO_LEVEL: int(lst[2])}
    return res


def conditions_to_string(conditions):
    res = ''
    if conditions:
        res = ', '.join(f'{key}{version_to_string(value)}' for key, value in conditions.items())
    return res


def conditions_from_string(val):
    if not val:
        return {}
    val = val.split(';')[0]
    conditions = val.split(',')
    if not conditions:
        return {}
    pattern = r'(==|!=|<=|>=|<|>|~=)\s*([\d.]+)'
    res = {}
    for condition in conditions:
        key, value = re.fullmatch(pattern, condition.strip()).groups()
        res[key] = version_from_string(value)
    return res


def version_key(v):
    return tuple(map(int, v.split('.')))


def find_max_version(vers, conditions):
    if isinstance(conditions, str):
        conditions = conditions_from_string(conditions)
    res = None
    for val in vers:
        ver = version_from_string(val)
        if check_version(ver, conditions):
            if res is None:
                res = ver
            elif check_version(ver, {'>': res}):
                res = ver
    return res


def check_version(ver, conditions):
    try:
        res = _check_version(ver, conditions)
        return res
    except Exception as ex:
        logging.exception(ex)
        return False


def _check_version(version, conditions):
    if isinstance(version, str):
        version = version_from_string(version)
    if isinstance(conditions, str):
        conditions = conditions_from_string(conditions)
    if not version:
        return True
    if not conditions:
        return True
    for (condition, value) in conditions.items():
        if condition == '==':
            for level in VERSION_LEVELS:
                if version[level] != value[level]:
                    return False
        elif condition == '>':
            for level in VERSION_LEVELS:
                if version[level] > value[level]:
                    break
                elif version[level] < value[level]:
                    return False
        elif condition == '<':
            for level in VERSION_LEVELS:
                if version[level] < value[level]:
                    break
                elif version[level] > value[level]:
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
        elif condition == '!=':
            res = False
            for level in VERSION_LEVELS:
                if version[level] != value[level]:
                    res = True
                    break
            return res
        elif condition == '~=':
            for level in (MAJOR_LEVEL, MINOR_LEVEL):
                if version[level] != value[level]:
                    return False
        else:
            return False
    return True


pattern = r"""
    ^
    (?P<package_name>[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*)
    (?P<version_spec>[^;]*)
    (?:;\s*(?P<markers>.+))?
    $
"""

python_version_pattern = r"""
    python_version\s*
    (?P<constraints>(?:(?:<|<=|==|>=|>|!=)\s*['"]?[0-9._*]+['"]?(?:\s*,\s*)?)+)
"""

extra_pattern = r"""
    extra\s*
    ==\s*
    ['"](?P<extra_name>[a-zA-Z0-9_-]+)['"]
"""

regex = re.compile(pattern, re.VERBOSE | re.IGNORECASE)
python_version_regex = re.compile(python_version_pattern, re.VERBOSE | re.IGNORECASE)
extra_regex = re.compile(extra_pattern, re.VERBOSE | re.IGNORECASE)


def parse_requires_dist(requires_dist):
    decoded_str = html.unescape(requires_dist)
    match = regex.match(decoded_str.strip())
    if match:
        result = match.groupdict()
        result = {k: v.strip() if v else None for k, v in result.items()}
        markers = result.pop('markers', None)
        if markers:
            py_matches = python_version_regex.finditer(markers)
            constraints = []
            for match in py_matches:
                for constraint in re.split(r'\s*,\s*', match.group('constraints')):
                    constraint = re.sub(r"\s*['\"]", "", constraint.strip())
                    constraint = re.sub(r"\s+", "", constraint)
                    if constraint:
                        constraints.append(constraint)
            if constraints:
                result['python_version'] = ",".join(constraints)
            extra_match = extra_regex.search(markers)
            if extra_match:
                result['extra'] = extra_match.group('extra_name')
        return result
    else:
        return None


def to_canonical(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[-_.]+', '-', name)
    name = re.sub(r'[^a-z0-9-]', '', name)
    name = name.strip('-')
    return name
