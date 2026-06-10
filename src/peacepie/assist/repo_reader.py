import json
import logging
import os
import sqlite3
import urllib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.parser import Parser
from pathlib import Path
from importlib import resources
from urllib.parse import urlparse
from urllib.request import urlopen

from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name

from peacepie import params


class RepoReader:

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON;')
        try:
            yield conn
            conn.commit()
        except Exception as e:
            logging.exception(e)
        finally:
            conn.close()

    def __init__(self, parent):
        self.parent = parent
        self.db_dir = Path(params.get_param('db_dir', '../databases'))
        self.db_path = self.db_dir / 'repo_cache.db'
        self.db_dir.mkdir(exist_ok=True)
        if self.db_path.is_file():
            with self._connect() as conn:
                cursor = conn.cursor()
                now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                cursor.execute('DELETE FROM json_responses WHERE expires_at < ?', (now,))
                cursor.execute('DELETE FROM metadata WHERE expires_at < ?', (now,))
                cursor.execute('DELETE FROM wheels WHERE expires_at < ?', (now,))
            return
        sql_resource = resources.files('peacepie') / 'resources' / 'repo_cache.sql'
        script = sql_resource.read_text(encoding='utf-8')
        try:
            with self._connect() as conn:
                conn.executescript(script)
        except Exception as e:
            logging.exception(e)

    def get_json(self, index_url, package_name):
        query = 'SELECT * FROM json_responses WHERE index_url = ? AND package_name = ?'
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (index_url, package_name,))
            res = cursor.fetchone()
            row = dict(res) if res else None
            if row:
                if datetime.fromisoformat(row.get('expires_at')) < datetime.now(timezone.utc).replace(tzinfo=None):
                    cursor.execute('DELETE FROM json_responses WHERE id = ?', (row.get('id'),))
                else:
                    logging.debug(f'Simple Repository JSON response for package "{package_name}" is fetched')
                    return json.loads(row.get('data'))
        data = self.download_json(index_url, package_name)
        if not data:
            return None
        query = 'INSERT INTO json_responses (index_url, package_name, expires_at, data) VALUES (?, ?, ?, ?)'
        expires_at = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)).isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (index_url, package_name, expires_at, data))
        return json.loads(data)

    def download_json(self, index_url, package_name):
        url = f'{index_url}/simple/{package_name}/?format=application/vnd.pypi.simple.v1+json'
        for attempt in range(self.parent.max_retries):
            if self.parent.resolver.exit_flag:
                return None
            try:
                logging.debug(f'Try {attempt + 1} to download Simple Repository JSON response for package: "{package_name}"')
                with urlopen(url, timeout=10) as response:
                    res = response.read().decode('utf-8')
                    logging.debug(f'Simple Repository JSON response for package "{package_name}" is downloaded')
                    return res
            except Exception as e:
                logging.error(e)
        return None

    def get_metadata(self, url, package_name, package_version):
        log_name = f'{package_name.replace('-', '_')}-{package_version}'
        query = 'SELECT * FROM metadata WHERE url = ? AND package_name = ? AND package_version = ?'
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (url, package_name, package_version))
            res = cursor.fetchone()
            row = dict(res) if res else None
            if row:
                if datetime.fromisoformat(row.get('expires_at')) < datetime.now(timezone.utc).replace(tzinfo=None):
                    cursor.execute('DELETE FROM metadata WHERE id = ?', (row.get('id'),))
                else:
                    logging.debug(f'METADATA for package {log_name} is fetched')
                    return json.loads(row.get('data')).get('requires')
        requires = self.download_metadata(url, log_name)
        if requires is None:
            return None
        query = 'INSERT INTO metadata (url, package_name, package_version, expires_at, data) VALUES (?, ?, ?, ?, ?)'
        expires_at = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)).isoformat()
        data = json.dumps({'requires': requires})
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (url, package_name, package_version, expires_at, data))
        return requires

    def download_metadata(self, url, log_name):
        url = f'{url}.metadata'
        metadata = None
        for attempt in range(self.parent.max_retries):
            if self.parent.resolver.exit_flag:
                return None
            try:
                logging.debug(f'Try {attempt + 1} to download METADATA for package: {log_name}')
                with urlopen(url, timeout=10) as response:
                    metadata = response.read().decode('utf-8')
                    logging.debug(f'METADATA for package {log_name} is downloaded')
                    break
            except Exception as e:
                logging.error(e)
        if not metadata:
            return None
        msg = Parser().parsestr(metadata)
        str_requires = msg.get_all('Requires-Dist', [])
        requires = []
        for str_require in str_requires:
            try:
                req = Requirement(str_require)
                req.name = canonicalize_name(req.name)
            except InvalidRequirement:
                continue
            except Exception as e:
                logging.error(e)
                continue
            requires.append(str(req))
        return requires

    def get_wheel(self, url, package_name, package_version):
        log_name = f'{package_name.replace('-', '_')}-{package_version}'
        query = 'SELECT * FROM wheels WHERE url = ? AND package_name = ? AND package_version = ?'
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (url, package_name, package_version))
            res = cursor.fetchone()
            row = dict(res) if res else None
            if row:
                if datetime.fromisoformat(row.get('expires_at')) < datetime.now(timezone.utc).replace(tzinfo=None):
                    cursor.execute('DELETE FROM wheels WHERE id = ?', (row.get('id'),))
                else:
                    data = row.get('data')
                    if os.path.exists(data) and os.path.isfile(data):
                        logging.debug(f'Wheel for package {log_name} is fetched')
                        return data
                    else:
                        cursor.execute('DELETE FROM wheels WHERE id = ?', (row.get('id'),))
        data = self.download_wheel(url, log_name)
        if data is None:
            return None
        query = 'INSERT INTO wheels (url, package_name, package_version, expires_at, data) VALUES (?, ?, ?, ?, ?)'
        expires_at = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)).isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (url, package_name, package_version, expires_at, data))
        return data

    def download_wheel(self, url, log_name):
        folder_name, file_name = self.get_wheel_path(url)
        os.makedirs(folder_name, exist_ok=True)
        wheel_path = f'{folder_name}/{file_name}'
        with urllib.request.urlopen(url, timeout=20) as response:
            with open(wheel_path, 'wb') as out_file:
                chunk_size = 8192
                while True:
                    if self.parent.installer.exit_flag:
                        logging.debug(f'Exit from loading for {log_name}')
                        return False
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
        logging.debug(f'Wheel for package {log_name} is downloaded')
        return wheel_path

    def get_wheel_path(self, url):
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        file_name = path_parts[-1]
        path_parts = path_parts[1:2]
        path_segments = [p for p in path_parts if p]
        name_parts = []
        if parsed.scheme:
           name_parts.append(parsed.scheme)
        if parsed.netloc:
            netloc_clean = parsed.netloc.replace(':', '_')
            name_parts.append(netloc_clean)
        name_parts.extend(path_segments)
        folder_name = '_'.join(name_parts)
        unsafe_chars = r'\/:*?"<>|'
        for ch in unsafe_chars:
            folder_name = folder_name.replace(ch, '_')
        return f'{self.parent.cache_path}/{folder_name}', file_name
