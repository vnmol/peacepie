from pathlib import Path
from importlib.metadata import Distribution
from packaging.requirements import Requirement

def get_package_info_and_requires(dist_info_path, extras=None):
    extras = extras if extras else []
    dist_info = Path(dist_info_path) if isinstance(dist_info_path, str) else dist_info_path
    if not dist_info.exists() or not dist_info.is_dir():
        raise FileNotFoundError(f'Folder "{dist_info_path}" is not found')
    dist = Distribution.at(dist_info)
    name = dist.metadata.get("Name")
    version = dist.metadata.get("Version")
    dependencies = []
    for req_str in (dist.metadata.get_all("Requires-Dist") or []):
        req = Requirement(req_str)
        res = {'package_name': req.name, 'extras': req.extras, 'version_spec': str(req.specifier)}
        if not req.marker:
            dependencies.append(res)
            continue
        if 'extra' in str(req.marker):
            for extra in extras:
                if req.marker.evaluate(environment={'extra': extra}):
                    dependencies.append(res)
                    break
        else:
            if req.marker.evaluate():
                dependencies.append(res)
    return name, version, dependencies



# ============ ПРИМЕР ИСПОЛЬЗОВАНИЯ ============
if __name__ == "__main__":
    dist_info_dir = "/home/vmol/PycharmProjects/peacepie_project/packages/instance_01/tmp/simple_fastapi_dashboard-0.0.1/simple_fastapi_dashboard-0.0.1.dist-info"
    selected_extras = ["standard"]
    try:
        print(get_package_info_and_requires(dist_info_dir, extras=selected_extras))
    except Exception as e:
        print(f"❌ Ошибка: {e}")