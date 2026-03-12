import os
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from core import config, security, zmq_client
from api.emulator import emulator


DB_PATH = "/home/vmol/PycharmProjects/peacepie_project/databases/users.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn


def dict_from_row(row):
    return dict(zip(row.keys(), row))


router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
async def read_root(request: Request, user=Depends(security.get_current_user)):
    file_path = os.path.join("templates", "users_vue.html")
    content = ''
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    return templates.TemplateResponse("users.html", {"request": request, "user": user, "content": content})


@router.get("/api/packs")
async def get_packs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM packs ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


@router.post("/api/packs")
async def create_pack(pack: dict):
    name = pack.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO packs (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM packs WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Pack name already exists")


@router.put("/api/packs/{pack_id}")
async def update_pack(pack_id: int, pack: dict):
    name = pack.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE packs SET name = ? WHERE id = ? AND builtin = FALSE", (name, pack_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Pack not found or is builtin")
        conn.commit()
        cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="New pack name already exists")


@router.delete("/api/packs/{pack_id}")
async def delete_pack(pack_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM packs WHERE id = ? AND builtin = FALSE", (pack_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Pack not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "Pack deleted successfully"}


# --- Classes Endpoints ---
@router.get("/api/classes")
async def get_classes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


@router.post("/api/classes")
async def create_class(cls: dict):
    pack_id = cls.get("pack_id")
    name = cls.get("name")
    if not pack_id or not name:
        raise HTTPException(status_code=400, detail="Pack ID and Name are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO classes (pack_id, name) VALUES (?, ?)", (pack_id, name))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM classes WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Class name already exists in this pack")


@router.put("/api/classes/{class_id}")
async def update_class(class_id: int, cls: dict):
    pack_id = cls.get("pack_id")
    name = cls.get("name")
    if not pack_id or not name:
        raise HTTPException(status_code=400, detail="Pack ID and Name are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE classes SET pack_id = ?, name = ? WHERE id = ? AND builtin = FALSE",
                       (pack_id, name, class_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Class not found or is builtin")
        conn.commit()
        cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="New class name already exists in this pack")

@router.delete("/api/classes/{class_id}")
async def delete_class(class_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Исправлено: используем 'id' вместо 'class_id' в WHERE clause
    cursor.execute("DELETE FROM classes WHERE id = ? AND builtin = FALSE", (class_id,))
    if cursor.rowcount == 0:
        conn.close()
        # Возвращаем 404, если запись не найдена или является builtin
        raise HTTPException(status_code=404, detail="Class not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "Class deleted successfully"}

# --- Commands Endpoints ---
@router.get("/api/commands")
async def get_commands():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM commands ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


@router.post("/api/commands")
async def create_command(cmd: dict):
    class_id = cmd.get("class_id")
    name = cmd.get("name")
    if not class_id or not name:
        raise HTTPException(status_code=400, detail="Class ID and Name are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO commands (class_id, name) VALUES (?, ?)", (class_id, name))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM commands WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Command name already exists in this class")


@router.put("/api/commands/{command_id}")
async def update_command(command_id: int, cmd: dict):
    class_id = cmd.get("class_id")
    name = cmd.get("name")
    if not class_id or not name:
        raise HTTPException(status_code=400, detail="Class ID and Name are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE commands SET class_id = ?, name = ? WHERE id = ? AND builtin = FALSE",
                       (class_id, name, command_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Command not found or is builtin")
        conn.commit()
        cursor.execute("SELECT * FROM commands WHERE id = ?", (command_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="New command name already exists in this class")


@router.delete("/api/commands/{command_id}")
async def delete_command(command_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM commands WHERE id = ? AND builtin = FALSE", (command_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Command not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "Command deleted successfully"}


# --- Roles Endpoints ---
@router.get("/api/roles")
async def get_roles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roles ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


@router.post("/api/roles")
async def create_role(role: dict):
    name = role.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO roles (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM roles WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Role name already exists")


@router.put("/api/roles/{role_id}")
async def update_role(role_id: int, role: dict):
    name = role.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE roles SET name = ? WHERE id = ? AND builtin = FALSE", (name, role_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Role not found or is builtin")
        conn.commit()
        cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="New role name already exists")


@router.delete("/api/roles/{role_id}")
async def delete_role(role_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM roles WHERE id = ? AND builtin = FALSE", (role_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Role not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "Role deleted successfully"}


# --- Role Commands Endpoints ---
@router.get("/api/role_commands")
async def get_role_commands():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rc.role_id, rc.command_id, r.name as role_name, c.name as command_name, cl.name as class_name, p.name as pack_name, rc.builtin
        FROM role_commands rc
        JOIN roles r ON rc.role_id = r.id
        JOIN commands c ON rc.command_id = c.id
        JOIN classes cl ON c.class_id = cl.id
        JOIN packs p ON cl.pack_id = p.id
        ORDER BY rc.role_id, rc.command_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"role_id": row["role_id"], "command_id": row["command_id"],
             "role_name": row["role_name"], "command_name": row["command_name"],
             "class_name": row["class_name"], "pack_name": row["pack_name"],
             "builtin": row["builtin"]} for row in rows]


@router.post("/api/role_commands")
async def create_role_command(rc: dict):
    role_id = rc.get("role_id")
    command_id = rc.get("command_id")
    if not role_id or not command_id:
        raise HTTPException(status_code=400, detail="Role ID and Command ID are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO role_commands (role_id, command_id) VALUES (?, ?)", (role_id, command_id))
        conn.commit()
        conn.close()
        return rc
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="This role-command association already exists")


@router.delete("/api/role_commands/{role_id}/{command_id}")
async def delete_role_command(role_id: int, command_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM role_commands WHERE role_id = ? AND command_id = ? AND builtin = FALSE",
                   (role_id, command_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Role-command association not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "Role-command association removed successfully"}


# --- Users Endpoints ---
@router.get("/api/users")
async def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, builtin FROM users ORDER BY id")  # Не возвращаем хэши паролей
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


@router.post("/api/users")
async def create_user(user: dict):
    name = user.get("name")
    password = user.get("password")  # В реальном приложении пароль нужно хэшировать
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Заглушка для хэширования. В реальности используйте pbkdf2 или bcrypt.
        # Здесь просто сохраняем имя пользователя как "хэш" для демонстрации.
        pass_hash = f"dummy_hash_for_{name}_{password}" if password else None
        salt = "dummy_salt"
        iterations = 100000
        algorithm = "pbkdf2:sha256"

        cursor.execute("""
            INSERT INTO users (name, pass_hash, salt, iterations, algorithm)
            VALUES (?, ?, ?, ?, ?)
        """, (name, pass_hash, salt, iterations, algorithm))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT id, name, builtin FROM users WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")


@router.put("/api/users/{user_id}")
async def update_user(user_id: int, user: dict):
    name = user.get("name")
    password = user.get("password")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Обновление пароля опционально
        if password:
            # Заглушка для хэширования
            pass_hash = f"dummy_hash_for_{name}_{password}"
            salt = "dummy_salt"
            iterations = 100000
            algorithm = "pbkdf2:sha256"
            cursor.execute("""
                UPDATE users SET name = ?, pass_hash = ?, salt = ?, iterations = ?, algorithm = ?
                WHERE id = ? AND builtin = FALSE
            """, (name, pass_hash, salt, iterations, algorithm, user_id))
        else:
            cursor.execute("UPDATE users SET name = ? WHERE id = ? AND builtin = FALSE", (name, user_id))

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found or is builtin")
        conn.commit()
        cursor.execute("SELECT id, name, builtin FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict_from_row(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="New username already exists")


@router.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND builtin = FALSE", (user_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "User deleted successfully"}


# --- User Roles Endpoints ---
@router.get("/api/user_roles")
async def get_user_roles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ur.user_id, ur.role_id, u.name as user_name, r.name as role_name, ur.builtin
        FROM user_roles ur
        JOIN users u ON ur.user_id = u.id
        JOIN roles r ON ur.role_id = r.id
        ORDER BY ur.user_id, ur.role_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": row["user_id"], "role_id": row["role_id"],
             "user_name": row["user_name"], "role_name": row["role_name"],
             "builtin": row["builtin"]} for row in rows]


@router.post("/api/user_roles")
async def create_user_role(ur: dict):
    user_id = ur.get("user_id")
    role_id = ur.get("role_id")
    if not user_id or not role_id:
        raise HTTPException(status_code=400, detail="User ID and Role ID are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))
        conn.commit()
        conn.close()
        return ur
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="This user-role association already exists")


@router.delete("/api/user_roles/{user_id}/{role_id}")
async def delete_user_role(user_id: int, role_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_roles WHERE user_id = ? AND role_id = ? AND builtin = FALSE", (user_id, role_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User-role association not found or is builtin")
    conn.commit()
    conn.close()
    return {"message": "User-role association removed successfully"}
