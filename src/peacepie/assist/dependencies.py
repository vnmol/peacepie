from pathlib import Path
from importlib.metadata import Distribution
from packaging.requirements import Requirement

def get_package_info_and_requires(dist_info_path):
    dist_info = Path(dist_info_path) if isinstance(dist_info_path, str) else dist_info_path
    if not dist_info.exists() or not dist_info.is_dir():
        raise FileNotFoundError(f'Folder "{dist_info_path}" is not found')
    dist = Distribution.at(dist_info)
    name = dist.metadata.get("Name")
    ver = dist.metadata.get("Version")
    dependencies = []
    for req_str in (dist.metadata.get_all("Requires-Dist") or []):
        req = Requirement(req_str)
        res = {'package_name': req.name, 'version_spec': str(req.specifier)}
        if not req.marker:
            dependencies.append(res)
            continue
        if req.marker.evaluate():
            dependencies.append(res)
        extras = req.extras if req.extras else set()
        for extra in extras:
            if req.marker.evaluate(environment={'extra': extra}):
                dependencies.append({'package_name': f'{req.name}[{extra}]', 'version_spec': str(req.specifier)})
    return name, ver, dependencies
