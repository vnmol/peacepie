import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from importlib import resources

from peacepie import params

from peacepie.control.accounts import password_hasher


class DbAdmin:

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
        admin += 'INSERT INTO user_roles (user_id, role_id) VALUES (1, 1);\n\n'
        sql_resource = resources.files('peacepie') / 'resources' / 'script.sql'
        script = sql_resource.read_text(encoding='utf-8')
        script += admin
        try:
            with self._connect() as conn:
                conn.executescript(script)
        except Exception as e:
            logging.exception(e)

    def get_user_by_name(self, username):
        query = "SELECT * FROM users WHERE name = ?"
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (username,))
            res = cursor.fetchone()
            user = dict(res) if res else None
        return user

    def access_check(self, user, pack, clss, command):
        res = False
        query = """
            SELECT 1
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id
            JOIN role_commands rc ON rc.role_id = r.id
            JOIN class_commands cc ON cc.id = rc.class_command_id
            JOIN commands cmd ON cmd.id = cc.command_id
            JOIN classes cls ON cls.id = cc.class_id
            JOIN pack_classes pc ON pc.class_id = cls.id
            JOIN packs p ON p.id = pc.pack_id
            WHERE u.name = ?
                AND (p.name = ? OR p.name = '*')
                AND (cls.name = ? OR cls.name = '*')
                AND (cmd.name = ? OR cmd.name = '*')
            LIMIT 1       
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (user, pack, clss, command))
            res = cursor.fetchone() is not None
        return res

    def get_packs(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM packs ORDER BY builtin desc, name")
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_pack(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO packs (name) VALUES (?)", (name,))
                new_id = cursor.lastrowid
                cursor.execute("SELECT * FROM packs WHERE id = ?", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def update_pack(self, pack_id, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE packs SET name = ? WHERE id = ? AND builtin = FALSE",
                               (name, pack_id))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Pack not found or is builtin'}
                cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_pack(self, pack_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM packs WHERE id = ?", (pack_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Pack not found or is builtin'}
                return {'status': 'success', 'data': 'Pack deleted successfully'}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def get_classes(self, pack_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT pc.id, pc.pack_id, c.name, (p.builtin and c.builtin) as builtin 
            FROM pack_classes pc 
            JOIN packs p ON pc.pack_id = p.id
            JOIN classes c ON pc.class_id = c.id
            WHERE pc.pack_id = ?
            ORDER BY builtin desc, c.name
            """, (pack_id,))
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_class(self, pack_id, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM packs WHERE id = ?", (pack_id,))
                pack = cursor.fetchone()
                if not pack:
                    return {'status': 'error', 'data': f'Pack with ID {pack_id} does not exist'}
                cursor.execute("SELECT id FROM classes WHERE name = ?", (name,))
                clss = cursor.fetchone()
                if clss:
                    class_id = clss[0]
                else:
                    cursor.execute("INSERT INTO classes (name) VALUES (?)",(name, ))
                    class_id = cursor.lastrowid
                cursor.execute("INSERT INTO pack_classes (pack_id, class_id) VALUES (?, ?)",
                               (pack_id, class_id))
                new_id = cursor.lastrowid
                cursor.execute("""
                SELECT pc.id, pc.pack_id, c.name, (p.builtin and c.builtin) as builtin 
                FROM pack_classes pc 
                JOIN packs p ON pc.pack_id = p.id
                JOIN classes c ON pc.class_id = c.id
                WHERE pc.id = ?""", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_class(self, pack_class_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM pack_classes WHERE id = ?", (pack_class_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Class not found or is builtin'}
                return {'status': 'success', 'data': 'Class deleted successfully'}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def get_commands(self, class_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cc.id, cc.class_id, com.name, (com.builtin and cls.builtin and pack.builtin) as builtin
                FROM class_commands cc
                JOIN commands com ON cc.command_id = com.id
                JOIN pack_classes pc ON cc.class_id = pc.id
                JOIN classes cls ON pc.class_id = cls.id
                JOIN packs pack ON pc.pack_id = pack.id
                WHERE cc.class_id = ?
                ORDER BY builtin desc, com.name""", (class_id,))
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_command(self, class_id, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM pack_classes WHERE id = ?", (class_id,))
                clss = cursor.fetchone()
                if not clss:
                    return {'status': 'error', 'data': f'Class with ID {class_id} does not exist'}
                cursor.execute("SELECT id FROM commands WHERE name = ?", (name,))
                command = cursor.fetchone()
                if command:
                    command_id = command[0]
                else:
                    cursor.execute("INSERT INTO commands (name) VALUES (?)", (name,))
                    command_id = cursor.lastrowid
                cursor.execute("INSERT INTO class_commands (class_id, command_id) VALUES (?, ?)",
                               (class_id, command_id))
                new_id = cursor.lastrowid
                cursor.execute("""
                    SELECT cc.id, cc.class_id, com.name, (com.builtin and cls.builtin and pack.builtin) as builtin
                    FROM class_commands cc
                    JOIN commands com ON cc.command_id = com.id
                    JOIN pack_classes pc ON cc.class_id = pc.id
                    JOIN classes cls ON pc.class_id = cls.id
                    JOIN packs pack ON pc.pack_id = pack.id
                    WHERE cc.id = ?
                    ORDER BY builtin desc, com.name""", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_command(self, class_command_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM class_commands WHERE id = ?", (class_command_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Command not found or is builtin'}
                return {'status': 'success', 'data': {'message': 'Command deleted successfully'}}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def get_roles(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM roles ORDER BY builtin desc, name")
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_role(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO roles (name) VALUES (?)", (name,))
                new_id = cursor.lastrowid
                cursor.execute("SELECT * FROM roles WHERE id = ?", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def update_role(self, role_id, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE roles SET name = ? WHERE id = ?",(name, role_id))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Role not found or is builtin'}
                cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_role(self, role_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM roles WHERE id = ?", (role_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Role not found or is builtin'}
                return {'status': 'success', 'data': {'message': 'Role deleted successfully'}}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def get_role_commands(self, role_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    rc.id, rc.role_id, 
                    (p.name || ':' || c.name || ':' || com.name) as name,
                    (p.builtin and c.builtin and com.builtin and r.builtin) as builtin
                FROM role_commands rc
                JOIN roles r ON rc.role_id = r.id
                JOIN class_commands cc ON rc.class_command_id = cc.id
                JOIN commands com ON cc.command_id = com.id
                JOIN pack_classes pc ON cc.class_id = pc.id 
                JOIN classes c ON pc.class_id = c.id
                JOIN packs p ON pc.pack_id = p.id
                WHERE rc.role_id = ? ORDER BY builtin desc, name""", (role_id,))
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_role_command(self, role_id, command_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM roles WHERE id = ?", (role_id,))
                row = cursor.fetchone()
                if not row:
                    return {'status': 'existence_error', 'data': f'Role with ID {role_id} does not exist'}
                cursor.execute("SELECT id FROM class_commands WHERE id = ?", (command_id,))
                row = cursor.fetchone()
                if not row:
                    return {'status': 'existence_error', 'data': f'Command with ID {command_id} does not exist'}
                cursor.execute("INSERT INTO role_commands (role_id, class_command_id) VALUES (?, ?)",
                               (role_id, command_id))
                new_id = cursor.lastrowid
                cursor.execute("""
                    SELECT
                        rc.id, rc.role_id, 
                        (p.name || ':' || c.name || ':' || com.name) as name,
                        (p.builtin and c.builtin and com.builtin and r.builtin) as builtin
                    FROM role_commands rc
                    JOIN roles r ON rc.role_id = r.id
                    JOIN class_commands cc ON rc.class_command_id = cc.id
                    JOIN commands com ON cc.command_id = com.id
                    JOIN pack_classes pc ON cc.class_id = pc.id 
                    JOIN classes c ON pc.class_id = c.id
                    JOIN packs p ON pc.pack_id = p.id
                    WHERE rc.id = ?""", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_role_command(self, role_command_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""DELETE FROM role_commands WHERE id = ?""", (role_command_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'Role-command association not found or is builtin'}
                return {'status': 'success', 'data': {'message': 'Role-command association removed successfully'}}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def get_users(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, builtin FROM users ORDER BY builtin desc, name")
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_user(self, name, password):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                hp = password_hasher.PasswordHasher.hash_password(password)
                cursor.execute("""
                    INSERT INTO users (name, pass_hash, salt, iterations, algorithm)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, hp.get("pass_hash"), hp.get("salt"), hp.get("iterations"), hp.get("algorithm")))
                new_id = cursor.lastrowid
                cursor.execute("SELECT id, name, builtin FROM users WHERE id = ?", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def update_user(self, user_id, name, password):
         with self._connect() as conn:
            cursor = conn.cursor()
            try:
                if password:
                    hp = password_hasher.PasswordHasher.hash_password(password)
                    cursor.execute('''UPDATE users
                                   SET name = ?, pass_hash = ?, salt = ?, iterations = ?, algorithm = ?
                                   WHERE id = ?''',
                                   (name, hp.get("pass_hash"), hp.get("salt"), hp.get("iterations"),
                                    hp.get("algorithm"), user_id))
                else:
                    cursor.execute("UPDATE users SET name = ? WHERE id = ?",(name, user_id))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'User not found or is builtin'}
                cursor.execute("SELECT id, name, builtin FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_user(self, user_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'User not found or is builtin'}
                return {'status': 'success', 'data': {'message': 'User deleted successfully'}}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}


    def get_user_roles(self, user_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ur.id, r.name, (u.builtin and r.builtin) as builtin
                FROM user_roles ur
                JOIN users u ON ur.user_id = u.id
                JOIN roles r ON ur.role_id = r.id
                WHERE u.id = ?
                ORDER BY builtin desc, r.name""", (user_id,))
            rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

    def create_user_role(self, user_id, role_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                               (user_id, role_id))
                new_id = cursor.lastrowid
                cursor.execute("""
                    SELECT ur.id, r.name, (u.builtin and r.builtin) as builtin
                    FROM user_roles ur
                    JOIN users u ON ur.user_id = u.id
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.id = ?""", (new_id,))
                row = cursor.fetchone()
                return {'status': 'success', 'data': dict_from_row(row)}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}

    def delete_user_role(self, user_role_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM user_roles WHERE id = ?",(user_role_id,))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'status': 'existence_error', 'data': 'User-role association not found or is builtin'}
                return {'status': 'success', 'data': {'message': 'User-role association removed successfully'}}
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return {'status': 'integrity_error', 'data': str(e)}


def dict_from_row(row):
    return dict(zip(row.keys(), row))