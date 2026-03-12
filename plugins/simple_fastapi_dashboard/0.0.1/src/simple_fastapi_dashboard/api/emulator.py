import sqlite3
from typing import Dict, Any, List, Tuple


# --- Файл: emulator.py ---
class DatabaseEmulator:
    """
    Эмулятор внешнего компонента с доступом к базе данных.
    Использует переданный путь к файлу SQLite базы данных.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Выполняет SELECT запрос."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def _execute_non_query(self, query: str, params: tuple = ()) -> int:
        """Выполняет INSERT, UPDATE, DELETE запросы."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def ask(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает входящее сообщение и возвращает ответ.
        """
        command = msg.get("command")
        body = msg.get("body", {})

        try:
            if command == "get_all_roles":
                return self._handle_get_all_roles()
            elif command == "get_role_privileges":
                role_id = body.get("role_id")
                return self._handle_get_role_privileges(role_id)
            elif command == "create_role":
                name = body.get("name")
                return self._handle_create_role(name)
            elif command == "delete_role":
                role_id = body.get("role_id")
                return self._handle_delete_role(role_id)
            elif command == "update_role_name":
                role_id = body.get("role_id")
                new_name = body.get("new_name")
                return self._handle_update_role_name(role_id, new_name)
            elif command == "assign_privilege":
                role_id = body.get("role_id")
                priv_id = body.get("privilege_id")
                return self._handle_assign_privilege(role_id, priv_id)
            elif command == "revoke_privilege":
                role_id = body.get("role_id")
                priv_id = body.get("privilege_id")
                return self._handle_revoke_privilege(role_id, priv_id)
            else:
                return {"status": "error", "message": f"Unknown command: {command}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _handle_get_all_roles(self) -> Dict[str, Any]:
        # Запрос для получения всех ролей
        roles_query = "SELECT id, name FROM roles WHERE builtin = 0 ORDER BY name;"
        raw_roles = self._execute_query(roles_query)

        # Преобразование в список словарей
        roles = [{"id": r[0], "name": r[1]} for r in raw_roles]

        return {
            "status": "success",
            "data": {
                "roles": roles,
            }
        }

    def _handle_get_role_privileges(self, role_id: int) -> Dict[str, Any]:
        """Обрабатывает запрос на получение привилегий для конкретной роли."""
        if not isinstance(role_id, int) or role_id <= 0:
             return {"status": "error", "message": "Invalid role ID."}

        # Запрос для получения привилегий, связанных с указанной ролью
        query = """
            SELECT p.id, p.pack_id, p.class_id, p.command_id
            FROM privileges p
            JOIN role_privileges rp ON p.id = rp.privilege_id
            WHERE rp.role_id = ? AND p.builtin = 0 AND rp.builtin = 0
            ORDER BY p.pack_id, p.class_id, p.command_id;
        """
        raw_privileges = self._execute_query(query, (role_id,))

        # Преобразование в список словарей
        privileges = [
            {"id": p[0], "pack_id": p[1], "class_id": p[2], "command_id": p[3]}
            for p in raw_privileges
        ]

        # Проверяем, существует ли роль
        role_exists_query = "SELECT 1 FROM roles WHERE id = ? AND builtin = 0;"
        if not self._execute_query(role_exists_query, (role_id,)):
            return {"status": "error", "message": "Role not found or is a built-in role."}

        return {
            "status": "success",
            "data": {
                "privileges": privileges
            }
        }


    def _handle_create_role(self, name: str) -> Dict[str, Any]:
        if not name or len(name.strip()) == 0:
            return {"status": "error", "message": "Role name cannot be empty."}
        try:
            insert_query = "INSERT INTO roles (name) VALUES (?);"
            new_id = self._execute_non_query(insert_query, (name.strip(),))
            return {"status": "success", "message": f"Role '{name}' created successfully.", "id": new_id}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": f"A role with the name '{name}' already exists."}

    def _handle_delete_role(self, role_id: int) -> Dict[str, Any]:
        # Проверка, что роль существует и не встроена
        check_query = "SELECT name FROM roles WHERE id = ? AND builtin = 0;"
        res = self._execute_query(check_query, (role_id,))
        if not res:
            return {"status": "error", "message": "Role not found or is a built-in role."}

        # Удаление привязок к правам
        delete_rp_query = "DELETE FROM role_privileges WHERE role_id = ?;"
        self._execute_non_query(delete_rp_query, (role_id,))

        # Удаление самой роли
        delete_role_query = "DELETE FROM roles WHERE id = ?;"
        self._execute_non_query(delete_role_query, (role_id,))
        return {"status": "success", "message": f"Role with ID {role_id} deleted successfully."}

    def _handle_update_role_name(self, role_id: int, new_name: str) -> Dict[str, Any]:
        if not new_name or len(new_name.strip()) == 0:
            return {"status": "error", "message": "New role name cannot be empty."}

        # Проверка, что роль существует и не встроена
        check_query = "SELECT name FROM roles WHERE id = ? AND builtin = 0;"
        res = self._execute_query(check_query, (role_id,))
        if not res:
            return {"status": "error", "message": "Role not found or is a built-in role."}

        try:
            update_query = "UPDATE roles SET name = ? WHERE id = ?;"
            self._execute_non_query(update_query, (new_name.strip(), role_id))
            return {"status": "success", "message": f"Role name updated to '{new_name}'."}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": f"A role with the name '{new_name}' already exists."}

    def _handle_assign_privilege(self, role_id: int, priv_id: int) -> Dict[str, Any]:
        # Проверка существования роли и права
        role_check = self._execute_query("SELECT 1 FROM roles WHERE id = ? AND builtin = 0;", (role_id,))
        priv_check = self._execute_query("SELECT 1 FROM privileges WHERE id = ? AND builtin = 0;", (priv_id,))
        if not role_check or not priv_check:
            return {"status": "error", "message": "Role or Privilege not found or is a built-in item."}

        try:
            insert_query = "INSERT INTO role_privileges (role_id, privilege_id) VALUES (?, ?);"
            self._execute_non_query(insert_query, (role_id, priv_id))
            return {"status": "success", "message": f"Privilege {priv_id} assigned to role {role_id}."}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "Privilege is already assigned to this role."}

    def _handle_revoke_privilege(self, role_id: int, priv_id: int) -> Dict[str, Any]:
        # Проверка существования привязки
        check_query = "SELECT 1 FROM role_privileges WHERE role_id = ? AND privilege_id = ? AND builtin = 0;"
        res = self._execute_query(check_query, (role_id, priv_id))
        if not res:
            return {"status": "error", "message": "Assignment not found or is a built-in assignment."}

        delete_query = "DELETE FROM role_privileges WHERE role_id = ? AND privilege_id = ?;"
        self._execute_non_query(delete_query, (role_id, priv_id))
        return {"status": "success", "message": f"Privilege {priv_id} revoked from role {role_id}."}


# --- Инициализация эмулятора ---
# Убедитесь, что файл script.sql находится в той же директории, что и этот скрипт.
emulator = DatabaseEmulator(db_path="/home/vmol/PycharmProjects/peacepie_project/databases/users.db")

if __name__ == "__main__":
    # Пример использования
    print("--- get_all_roles ---")
    print(emulator.ask({"command": "get_all_roles"}))
    print("\n--- get_role_privileges (ID 1) ---")
    print(emulator.ask({"command": "get_role_privileges", "body": {"role_id": 1}}))
    print("\n--- get_role_privileges (ID 999) ---")
    print(emulator.ask({"command": "get_role_privileges", "body": {"role_id": 999}}))
