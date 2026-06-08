import asyncio
import logging
import posixpath
from html.parser import HTMLParser

from pathlib import Path
from urllib.parse import urlparse

from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename, InvalidWheelFilename

from peacepie.assist.pack_tree import Node


class LinkParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.supported_tags = list(sys_tags())
        self.links = []
        self.in_a = False
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_a = True
            self.href = dict(attrs).get('href')

    def handle_data(self, data):
        if not (self.in_a and self.href):
            return
        name = data.strip()
        if not name.endswith('whl'):
            return
        try:
            _, ver, _, wheel_tags = parse_wheel_filename(name)
            if not wheel_tags.intersection(self.supported_tags):
                return
            self.links.append({'href': self.href, 'name': name, 'version': ver})
        except InvalidWheelFilename:
            pass
        except Exception as e:
            logging.error(e)

    def handle_endtag(self, tag):
        if tag == 'a' and self.in_a:
            self.in_a = False
            self.href = None


class PackResolver:

    def __init__(self, parent):
        self.parent = parent
        self.supported_tags = list(sys_tags())
        self.tree = None
        self.packs = None
        self.exit_flag = False
        self.queue = None

    async def exit(self):
        self.exit_flag = True
        if self.queue:
            await self.queue.get()

    async def resolve_package(self, index_url, requirement):
        logging.info('Start packages resolving')
        self.tree = Node(None, {'package_name': None, 'package_version': None})
        self.packs = {}
        self.queue = asyncio.Queue()
        res = await self.build_result(index_url, requirement)
        logging.info('Finish packages resolving')
        if self.exit_flag:
            await self.queue.put(1)
        else:
            self.queue = None
        return res

    async def build_result(self, index_url, requirement):
        if not await asyncio.to_thread(self.add_child, index_url, requirement, False, None, self.tree):
            return None
        res = {}
        stack = []
        stack.extend(self.tree.children)
        while stack:
            node = stack.pop()
            name = node.data.get('package_name')
            ver = node.data.get('package_version')
            extra = node.data.get('package_extra')
            key = name.replace('-', '_'), extra
            if not res.get(key):
                url = self.get_url(name, ver, extra)
                if url:
                    val = {'version': str(ver), 'url': url, 'bundle': node.get_bundle()}
                    if extra:
                        val['metadata'] = self.get_requires(name, ver, extra)
                    res[key] = val
            stack.extend(node.children)
        return res

    def get_url(self, package_name, package_version, package_extra):
        pack = self.packs.get(package_name)
        index = pack.get('indexes').get(package_version)
        ver_record = pack.get('versions')[index]
        if package_extra:
            name = f'{package_name.replace("-", "_")}[{package_extra}]-{str(package_version)}'
            if (Path(self.parent.source_path) / name).is_dir():
                return None
        elif ver_record.get('is_installed'):
            return None
        return ver_record.get('url')

    def add_child(self, index_url, requirement, is_extra, package_extra, parent):
        if self.exit_flag:
            return False
        versions = self.get_versions(index_url, requirement, package_extra)
        if not versions:
            return False
        node = None
        for version in versions:
            if self.exit_flag:
                return False
            parent.remove(node)
            package_name = requirement.name.replace('-', '_')
            if is_extra:
                package_name += f'[{package_extra}]'
            package_version = version.get('version')
            package_name = f'{package_name}-{package_version}'
            logging.debug(f'Package is selected: {package_name}')
            node = Node(parent,
                        {'package_name': requirement.name,
                         'package_version': package_version,
                         'package_extra': package_extra if is_extra else None})
            if not is_extra:
                extras = requirement.extras if requirement.extras else set()
                logging.debug(f'Extras for {package_name} are found: {extras}')
                for extra in extras:
                    if self.exit_flag:
                        return False
                    if not self.add_child(index_url, requirement, True, extra, parent):
                        break
            requires = self.get_requires(requirement.name, package_version, package_extra if is_extra else None)
            logging.debug(f'Requires for {package_name} are found: {requires}')
            for require in requires:
                if not self.add_child(index_url, require, False, package_extra, node):
                    break
            else:
                return True
        return False

    def get_versions(self, index_url, requirement, extra):
        pack = self.packs.get(requirement.name)
        if pack and self.tree:
            ver = self.tree.find_version(requirement.name)
            if ver:
                if check_requirement(ver, requirement, extra):
                    index = pack.get('indexes').get(ver)
                    return [pack.get('versions')[index]]
                else:
                    return None
        versions = pack.get('versions') if pack else self.add_pack(index_url, requirement.name)
        if not versions:
            return None
        versions = [ver for ver in versions if check_requirement(ver.get('version'), requirement, extra)]
        if len(versions) == 0:
            return None
        return versions

    def add_pack(self, index_url, package_name):
        data = None
        try:
            data = self.parent.repo_reader.get_json(index_url, package_name)
        except Exception as e:
            logging.error(e)
        if not data:
            return None
        versions = []
        for file in data.get('files'):
            if self.exit_flag:
                return None
            try:
                _, ver, _, wheel_tags = parse_wheel_filename(file.get('filename'))
                if not wheel_tags.intersection(self.supported_tags):
                    continue
                if ver.is_prerelease:
                    continue
                url = file.get('url')
                parsed = urlparse(url)
                if not (bool(parsed.scheme) or url.startswith('//')):
                    url = index_url + posixpath.normpath('/' + url)
                is_installed = (Path(self.parent.source_path) / f'{package_name.replace("-", "_")}-{str(ver)}').is_dir()
                version = {'is_installed': is_installed, 'version': ver, 'url': url, 'requires': None}
                versions.append(version)
            except InvalidWheelFilename:
                pass
            except Exception as e:
                logging.error(e)
        versions.sort(key=lambda d: (d['is_installed'], d['version']), reverse=True)
        indexes = {}
        for index, version in enumerate(versions):
            indexes[version.get('version')] = index
        self.packs[package_name] = {'indexes': indexes, 'versions': versions}
        return versions

    def get_requires(self, package_name, package_version, package_extra):
        pack = self.packs.get(package_name)
        index = pack.get('indexes').get(package_version)
        version = pack.get('versions')[index]
        rqs = version.get('requires')
        requires = rqs if rqs is not None else self.add_requires(version, package_name, str(package_version))
        res = {req for req in requires if check_marker(req.marker, package_extra)}
        if package_extra:
            res -= {req for req in requires if check_marker(req.marker, None)}
        return res

    def add_requires(self, version, package_name, package_version):
        res = self.parent.repo_reader.get_metadata(version.get('url'), package_name, package_version)
        if res is None:
            return None
        requires = [Requirement(rqr) for rqr in res]
        version['requires'] = requires
        return requires


def check_requirement(ver, requirement, extra):
    if ver not in requirement.specifier:
        return False
    return check_marker(requirement.marker, extra)


def check_marker(marker, extra):
    if not marker:
        return True
    if extra:
        return marker.evaluate({'extra': extra})
    else:
        return marker.evaluate()


def without_marker(requirement):
    parts = [requirement.name]
    if requirement.specifier:
        parts.append(str(requirement.specifier))
    new_req_str = ' '.join(parts)
    return Requirement(new_req_str)


'''
    Замена для add_pack, читает не json описание, а html страницу f'{index_url}/simple/{package_name}/'
    
    def add_pack_html(self, index_url, package_name):
        url = f'{index_url}/simple/{package_name}/'
        data = None
        for attempt in range(self.max_retries):
            if self.exit_flag:
                return None
            logging.debug(f'Try {attempt + 1} to download simple repository page for package: "{package_name}"')
            try:
                with urlopen(url, timeout=10) as response:
                    data = response.read().decode('utf-8')
                break
            except Exception as e:
                logging.error(e)
        if not data:
            logging.debug(f'Simple repository page for package: "{package_name}" is not found')
            return None
        logging.debug(f'Simple repository page for package: "{package_name}" is downloaded')
        parser = LinkParser()
        parser.feed(data)
        versions = []
        for link in parser.links:
            url = link.get('href')
            parsed = urlparse(url)
            parsed = parsed._replace(fragment='')
            url = str(urlunparse(parsed))
            if not (bool(parsed.scheme) or url.startswith('//')):
                url = index_url + posixpath.normpath('/' + url)
            ver = link.get('version')
            is_installed = (self.source_path / f'{package_name.replace("-", "_")}-{str(ver)}').is_dir()
            version = {'is_installed': is_installed, 'version': ver, 'url': url, 'requires': None}
            versions.append(version)
        versions.sort(key=lambda d: (d['is_installed'], d['version']), reverse=True)
        indexes = {}
        for index, version in enumerate(versions):
            indexes[version.get('version')] = index
        self.packs[package_name] = {'indexes': indexes, 'versions': versions}
        return versions
'''