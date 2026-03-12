import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from peacepie import params

from peacepie.control.accounts import password_hasher


class DbAdmin:

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def __init__(self, parent):
        self.parent = parent
        self.db_dir = Path(params.instance.get('db_dir'))
        self.db_path = self.db_dir / 'users.db'

    async def db_init(self):
        self.db_dir.mkdir(exist_ok=True)
        if self.db_path.is_file():
            return
        credentials = await self.parent.adaptor.get_credentials('account_admin')
        hp = password_hasher.PasswordHasher.hash_password(credentials.get('password'))
        admin = '\nINSERT INTO users (name, builtin, pass_hash, salt, iterations, algorithm) VALUES '
        admin += f'("{credentials.get("username")}", True, '
        admin += f'"{hp.get("pass_hash")}", "{hp.get("salt")}", {hp.get("iterations")}, "{hp.get("algorithm")}");\n\n'
        admin += 'INSERT INTO user_roles (user_id, role_id, builtin) VALUES (1, 1, TRUE);\n\n'
        with open(Path(__file__).resolve().parent / 'script.sql', 'r', encoding='utf-8') as f:
            script = f.read()
        script += admin
        try:
            with self._connect() as conn:
                conn.executescript(script)
        except Exception as e:
            logging.exception(e)

    def get_user_by_name(self, username):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM users WHERE name = ?"
            cursor.execute(query, (username,))
            user = dict(cursor.fetchone())
            cursor.close()
        return user
