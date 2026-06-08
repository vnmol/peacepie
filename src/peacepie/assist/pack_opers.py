import logging
from collections import defaultdict
from pathlib import Path
from importlib.metadata import Distribution
from packaging.requirements import Requirement

from peacepie.assist import version


def find_entry(path, package_name, version_spec, extras):
    root = path if isinstance(path, Path) else Path(path)
    entries = [str(item.name).split('-') for item in root.iterdir()
               if item.is_dir() and item.name.startswith(package_name) and len(str(item).split('-')) > 1]
    entries = [entry for entry in entries if version.check_version(entry[1], version_spec)]
    if not entries:
        return None
    pack_versions = {entry[1] for entry in entries if len(entry) == 2}
    extra_list = [{'version': entry[1], 'extra': entry[2]} for entry in entries
                  if len(entry) == 3 and entry[1] in pack_versions]
    extra_entries = {}
    for pack_version in pack_versions:
        extra_entries[pack_version] = set()
        for item in extra_list:
            extra_entries[item['version']].add(item['extra'])
    ver = None
    difference = None
    for pack_version in pack_versions:
        diff = extras - extra_entries.get(pack_version)
        if (difference is None or
                len(diff) < len(difference) or
                (len(diff) == len(difference) and (ver is None or version.check_version(pack_version, f'>{ver}')))):
            ver = pack_version
            difference = diff
    if not ver:
        return None
    res = {'package_name': package_name, 'version': ver, 'extras': difference}
    return res


def get_dist_info_path(path):
    root = path if isinstance(path, Path) else Path(path)
    for item in root.iterdir():
        if item.is_dir() and item.name.endswith('.dist-info'):
            return item
    return None

def get_package_info_and_requires(path, extras=None):
    dist_info_path = get_dist_info_path(path)
    extras = extras if extras else []
    dist_info = Path(dist_info_path) if isinstance(dist_info_path, str) else dist_info_path
    if not dist_info.exists() or not dist_info.is_dir():
        raise FileNotFoundError(f'Folder "{dist_info_path}" is not found')
    dist = Distribution.at(dist_info)
    name = dist.metadata.get('Name')
    version = dist.metadata.get('Version')
    dependencies = []
    for req_str in (dist.metadata.get_all("Requires-Dist") or []):
        req = Requirement(req_str)
        name = req.name.replace('-', '_')
        res = {'package_name': name, 'version_spec': str(req.specifier), 'extras': req.extras}
        if not req.marker:
            dependencies.append(res)
            continue
        if 'extra' in str(req.marker):
            for extra in extras:
                if req.marker.evaluate(environment={'extra': extra}):
                    res['extra'] = extra
                    dependencies.append(res)
                    break
        else:
            if req.marker.evaluate():
                dependencies.append(res)
    return name, version, dependencies
