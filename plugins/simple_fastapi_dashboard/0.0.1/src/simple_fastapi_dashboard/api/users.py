import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from core import security, zmq_client


router = APIRouter()

templates = Jinja2Templates(directory="templates")


# ─── Page route ─────────────────────────────────────────────────────────────

@router.get("/")
async def read_root(request: Request, user=Depends(security.get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    file_path = os.path.join("templates", "users_vue.html")
    content = ''
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    return templates.TemplateResponse("users.html", {"request": request, "user": user, "content": content})


# ─── Packs ───────────────────────────────────────────────────────────────────

@router.get("/api/packs")
async def get_packs(user=Depends(security.get_current_user)):
    msg = {'command': 'get_packs', 'body': None, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'packs':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/packs")
async def create_pack(pack: dict, user=Depends(security.get_current_user)):
    name = pack.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    msg = {'command': 'create_pack', 'body': {'name': name}, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'pack_is_created':
        return body.get('data')
    elif command == 'pack_is_not_created':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.put("/api/packs")
async def update_pack(pack: dict, user=Depends(security.get_current_user)):
    if not pack.get("pack_id") or not pack.get("name"):
        raise HTTPException(status_code=400, detail="ID and Name are required")
    msg = {'command': 'update_pack', 'body': pack, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'pack_is_updated':
        return body.get('data')
    elif command == 'pack_is_not_updated':
        match body.get('status'):
            case 'integrity_error' | 'existence_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/packs/{pack_id}")
async def delete_pack(pack_id: int, user=Depends(security.get_current_user)):
    body = {'pack_id': pack_id}
    msg = {'command': 'delete_pack', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'pack_is_deleted':
        return body.get('data')
    elif command == 'pack_is_not_deleted':
        match body.get('status'):
            case 'integrity_error' | 'existence_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


# ─── Classes ─────────────────────────────────────────────────────────────────

@router.get("/api/classes/{pack_id}")
async def get_classes(pack_id: int, user=Depends(security.get_current_user)):
    body = {'pack_id': pack_id}
    msg = {'command': 'get_classes', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'classes':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/classes")
async def create_class(cls: dict, user=Depends(security.get_current_user)):
    if not cls.get('pack_id') or not cls.get('name'):
        raise HTTPException(status_code=400, detail="Pack_id and Name are required")
    msg = {'command': 'create_class', 'body': cls, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'class_is_created':
        return body.get('data')
    elif command == 'class_is_not_created':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/classes/{pack_class_id}")
async def delete_class(pack_class_id: int, user=Depends(security.get_current_user)):
    body = {'pack_class_id': pack_class_id}
    msg = {'command': 'delete_class', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'class_is_deleted':
        return body.get('data')
    elif command == 'class_is_not_deleted':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


# ─── Commands ────────────────────────────────────────────────────────────────

@router.get("/api/commands/{class_id}")
async def get_commands(class_id, user=Depends(security.get_current_user)):
    body = {'class_id': class_id}
    msg = {'command': 'get_commands', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'commands':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/commands")
async def create_command(cmd: dict, user=Depends(security.get_current_user)):
    if not cmd.get("class_id") or not cmd.get("name"):
        raise HTTPException(status_code=400, detail="Name are required")
    msg = {'command': 'create_command', 'body': cmd, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'command_is_created':
        return body.get('data')
    elif command == 'command_is_not_created':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/commands/{class_command_id}")
async def delete_command(class_command_id: int, user=Depends(security.get_current_user)):
    body = {'class_command_id': class_command_id}
    msg = {'command': 'delete_command', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'command_is_deleted':
        return body.get('data')
    elif command == 'command_is_not_deleted':
        match body.get('status'):
            case 'existence_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


# ─── Roles ───────────────────────────────────────────────────────────────────

@router.get("/api/roles")
async def get_roles(user=Depends(security.get_current_user)):
    msg = {'command': 'get_roles', 'body': None, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'roles':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/roles")
async def create_role(role: dict, user=Depends(security.get_current_user)):
    if not role.get("name"):
        raise HTTPException(status_code=400, detail="Role Name are required")
    msg = {'command': 'create_role', 'body': role, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'role_is_created':
        return body.get('data')
    elif command == 'role_is_not_created':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.put("/api/roles")
async def update_role(role: dict, user=Depends(security.get_current_user)):
    if not role.get("role_id") or not role.get("name"):
        raise HTTPException(status_code=400, detail="Role ID and Name are required")
    msg = {'command': 'update_role', 'body': role, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'role_is_updated':
        return body.get('data')
    elif command == 'role_is_not_updated':
        match body.get('status'):
            case 'integrity_error' | 'existence_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/roles/{role_id}")
async def delete_role(role_id: int, user=Depends(security.get_current_user)):
    body = {'role_id': role_id}
    msg = {'command': 'delete_role', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'role_is_deleted':
        return body.get('data')
    elif command == 'role_is_not_deleted':
        match body.get('status'):
            case 'integrity_error' | 'existence_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


# ─── Role Commands ───────────────────────────────────────────────────────────

@router.get("/api/role_commands/{role_id}")
async def get_role_commands(role_id, user=Depends(security.get_current_user)):
    body = {'role_id': role_id}
    msg = {'command': 'get_role_commands', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'role_commands':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/role_commands")
async def create_role_command(rc: dict, user=Depends(security.get_current_user)):
    if not rc.get("role_id") or not rc.get("command_id"):
        raise HTTPException(status_code=400, detail="Role ID and Command ID are required")
    msg = {'command': 'create_role_command', 'body': rc, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'role_command_is_created':
        return body.get('data')
    elif command == 'role_command_is_not_created':
        match body.get('status'):
            case 'existence_error' | 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/role_commands/{role_command_id}")
async def delete_role_command(role_command_id: int, user=Depends(security.get_current_user)):
    body = {'role_command_id': role_command_id}
    msg = {'command': 'delete_role_command', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'role_command_is_deleted':
        return body.get('data')
    elif command == 'role_command_is_not_deleted':
        match body.get('status'):
            case 'existence_error' | 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


# ─── Users ───────────────────────────────────────────────────────────────────

@router.get("/api/users")
async def get_users(user=Depends(security.get_current_user)):
    msg = {'command': 'get_users', 'body': None, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'users':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/users")
async def create_user(user: dict, usr=Depends(security.get_current_user)):
    msg = {'command': 'create_user', 'body': user, 'recipient': 'account_admin', 'user': usr.get('username')}
    ans = zmq_client.client.ask(msg)
    body = ans.get('body')
    command = ans.get('command')
    if command == 'user_is_created':
        return body.get('data')
    elif command == 'user_is_not_created':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.put("/api/users")
async def update_user(user: dict, usr=Depends(security.get_current_user)):
    if not user.get('user_id') or not user.get("name"):
        raise HTTPException(status_code=400, detail="ID and Name are required")
    msg = {'command': 'update_user', 'body': user, 'recipient': 'account_admin', 'user': usr.get('username')}
    ans = zmq_client.client.ask(msg)
    body = ans.get('body')
    command = ans.get('command')
    if command == 'user_is_updated':
        return body.get('data')
    elif command == 'user_is_not_updated':
        match body.get('status'):
            case 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/users/{user_id}")
async def delete_user(user_id: int, user=Depends(security.get_current_user)):
    body = {'user_id': user_id}
    msg = {'command': 'delete_user', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'user_is_deleted':
        return body.get('data')
    elif command == 'user_is_not_deleted':
        match body.get('status'):
            case 'existence_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


# ─── User Roles ──────────────────────────────────────────────────────────────

@router.get("/api/user_roles/{user_id}")
async def get_user_roles(user_id, user=Depends(security.get_current_user)):
    body = {'user_id': user_id}
    msg = {'command': 'get_user_roles', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'user_roles':
        return body
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.post("/api/user_roles")
async def create_user_role(ur: dict, user=Depends(security.get_current_user)):
    if not ur.get("user_id") or not ur.get("role_id"):
        raise HTTPException(status_code=400, detail="User ID and Role ID are required")
    msg = {'command': 'create_user_role', 'body': ur, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'user_role_is_created':
        return body.get('data')
    elif command == 'user_role_is_not_created':
        match body.get('status'):
            case 'existence_error' | 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')


@router.delete("/api/user_roles/{user_role_id}")
async def delete_user_role(user_role_id: int, user=Depends(security.get_current_user)):
    body = {'user_role_id': user_role_id}
    msg = {'command': 'delete_user_role', 'body': body, 'recipient': 'account_admin', 'user': user.get('username')}
    ans = zmq_client.client.ask(msg)
    command = ans.get('command')
    body = ans.get('body')
    if command == 'user_role_is_deleted':
        return body.get('data')
    elif command == 'user_role_is_not_deleted':
        match body.get('status'):
            case 'existence_error' | 'integrity_error':
                raise HTTPException(status_code=400, detail=body.get('data'))
            case _:
                raise HTTPException(status_code=400, detail=f'Unknown error')
    elif command == 'access_denied':
        raise HTTPException(status_code=403, detail=f'Access denied')
    else:
        raise HTTPException(status_code=400, detail=f'Unknown error')
