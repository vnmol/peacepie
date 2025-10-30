import logging
import re
import html
import sys

VERSION = 'version'
MAJOR_LEVEL = 'major'
MINOR_LEVEL = 'minor'
MICRO_LEVEL = 'micro'
VERSION_LEVELS = (MAJOR_LEVEL, MINOR_LEVEL, MICRO_LEVEL)


def version_to_string(val):
    return f'{val[MAJOR_LEVEL]}.{val[MINOR_LEVEL]}.{val[MICRO_LEVEL]}'


def get_python_version():
    ver = version_from_string(sys.version)
    return ver


def version_from_string(val):
    if not val:
        return None
    is_prerelease = False
    suffix_start = 0
    for i, char in enumerate(val):
        if not char.isdigit() and char != '.':
            suffix_start = i
            is_prerelease = True
            break
    base_version = val[:suffix_start] if is_prerelease else val
    parts = base_version.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    micro = int(parts[2]) if len(parts) > 2 else 0
    return {MAJOR_LEVEL: major, MINOR_LEVEL: minor, MICRO_LEVEL: micro}


def conditions_to_string(conditions):
    res = ''
    if conditions:
        res = ', '.join(f'{key}{version_to_string(value)}' for key, value in conditions.items())
    return res


def conditions_from_string(val):
    constraints = val.split(',')
    parsed = []
    for constraint in constraints:
        constraint = constraint.strip()
        if not constraint:
            continue
        for op in ['!=', '>=', '<=', '>', '<', '==', '~=', '^=']:
            if constraint.startswith(op):
                ver = constraint[len(op):]
                parsed.append({op: version_from_string(ver)})
                break
        else:
            parsed.append({'==': constraint})
    return parsed


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
                res = ver, val
            elif check_version(ver, {'>': res}):
                res = ver, val
    if res is None:
        return None
    else:
        return res[1]


def check_version(ver, conditions):
    try:
        res = _check_version(ver, conditions)
        return res
    except Exception as ex:
        logging.info(f'ver: {ver}, conditions: {conditions}')
        logging.exception(ex)
        return False


def _check_version(version, conditions):
    if isinstance(version, str):
        version = version_from_string(version)
    if isinstance(conditions, str):
        if conditions.startswith('(') and conditions.endswith(')'):
            conditions = conditions[1:-1]
        conditions = conditions_from_string(conditions)
    if not version:
        return True
    if not conditions:
        return True
    for condition in conditions:
        key, value = next(iter(condition.items()))
        if key == '==':
            for level in VERSION_LEVELS:
                if version[level] != value[level]:
                    return False
            return True
        elif key == '>':
            for level in VERSION_LEVELS:
                if version[level] > value[level]:
                    return True
                elif version[level] < value[level]:
                    return False
            return False
        elif key == '<':
            for level in VERSION_LEVELS:
                if version[level] < value[level]:
                    return True
                elif version[level] > value[level]:
                    return False
            return False
        elif key == '>=':
            for level in VERSION_LEVELS:
                if version[level] > value[level]:
                    return True
                elif version[level] < value[level]:
                    return False
            return True
        elif key == '<=':
            for level in VERSION_LEVELS:
                if version[level] < value[level]:
                    return True
                elif version[level] > value[level]:
                    return False
            return True
        elif key == '!=':
            for level in VERSION_LEVELS:
                if version[level] != value[level]:
                    return True
            return False
        elif key == '~=':
            for level in (MAJOR_LEVEL, MINOR_LEVEL):
                if version[level] != value[level]:
                    return False
            return True
    return False


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

platform_system_pattern = r"""
    platform_system\s*
    ==\s*
    ['"](?P<platform_name>[a-zA-Z0-9_-]+)['"]
"""

extra_pattern = r"""
    extra\s*
    ==\s*
    ['"](?P<extra_name>[a-zA-Z0-9_-]+)['"]
"""

regex = re.compile(pattern, re.VERBOSE | re.IGNORECASE)
python_version_regex = re.compile(python_version_pattern, re.VERBOSE | re.IGNORECASE)
platform_system_regex = re.compile(platform_system_pattern, re.VERBOSE | re.IGNORECASE)
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
            platform_match = platform_system_regex.search(markers)
            if platform_match:
                result['platform_system'] = platform_match.group('platform_name')
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
