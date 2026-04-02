
from peacepie.control.accounts import db_admin, password_hasher


class AccountAdmin:

    def __init__(self):
        self.adaptor = None
        self.db_admin = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'start':
            await self.start(sender)
        elif command == 'authenticate':
            await self.authenticate(body, sender)
        elif command == 'access_check':
            await self.access_check(body, sender)
        elif command == 'get_packs':
            await self.get_packs(sender)
        elif command == 'create_pack':
            await self.create_pack(body.get('name'), sender)
        elif command == 'update_pack':
            await self.update_pack(body.get('pack_id'), body.get('name'), sender)
        elif command == 'delete_pack':
            await self.delete_pack(body.get('pack_id'), sender)
        elif command == 'get_classes':
            await self.get_classes(body.get('pack_id'), sender)
        elif command == 'create_class':
            await self.create_class(body.get('pack_id'), body.get('name'), sender)
        elif command == 'delete_class':
            await self.delete_class(body.get('pack_class_id'), sender)
        elif command == 'get_commands':
            await self.get_commands(body.get('class_id'), sender)
        elif command == 'create_command':
            await self.create_command(body.get('class_id'), body.get('name'), sender)
        elif command == 'delete_command':
            await self.delete_command(body.get('class_command_id'), sender)
        elif command == 'get_roles':
            await self.get_roles(sender)
        elif command == 'create_role':
            await self.create_role(body.get('name'), sender)
        elif command == 'update_role':
            await self.update_role(body.get('role_id'), body.get('name'), sender)
        elif command == 'delete_role':
            await self.delete_role(body.get('role_id'), sender)
        elif command == 'get_role_commands':
            await self.get_role_commands(body.get('role_id'), sender)
        elif command == 'create_role_command':
            await self.create_role_command(body.get('role_id'), body.get('command_id'), sender)
        elif command == 'delete_role_command':
            await self.delete_role_command(body.get('role_command_id'), sender)
        elif command == 'get_users':
            await self.get_users(sender)
        elif command == 'create_user':
            await self.create_user(body.get('name'), body.get('password'), sender)
        elif command == 'update_user':
            await self.update_user(body.get('user_id'), body.get('name'), body.get('password'), sender)
        elif command == 'delete_user':
            await self.delete_user(body.get('user_id'), sender)
        elif command == 'get_user_roles':
            await self.get_user_roles(body.get('user_id'), sender)
        elif command == 'create_user_role':
            await self.create_user_role(body.get('user_id'), body.get('role_id'), sender)
        elif command == 'delete_user_role':
            await self.delete_user_role(body.get('user_role_id'), sender)
        else:
            return False
        return True

    async def start(self, recipient):
        self.db_admin = db_admin.DbAdmin(self)
        await self.db_admin.db_init()
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))

    async def authenticate(self, credentials, recipient):
        if recipient is None:
            return
        user = self.db_admin.get_user_by_name(credentials.get('username'))
        body = None
        command = 'is_not_authenticated'
        if user and password_hasher.PasswordHasher.verify_password(credentials.get('password'), user):
            body = {'username': user.get('name')}
            command = 'is_authenticated'
        await self.adaptor.send(self.adaptor.get_msg(command, body, recipient))

    async def access_check(self, body, recipient):
        res = self.db_admin.access_check(body.get('user'), body.get('pack'), body.get('class'), body.get('command'))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('access' if res else 'access_denied', None, recipient))
        return res

    async def get_packs(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('packs', self.db_admin.get_packs(), recipient))

    async def create_pack(self, name, recipient):
        if not recipient:
            return
        res = self.db_admin.create_pack(name)
        if not res:
            res = {'status': 'error'}
        command = 'pack_is_created' if res.get('status') == 'success' else 'pack_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def update_pack(self, pack_id, name, recipient):
        if not recipient:
            return
        res = self.db_admin.update_pack(pack_id, name)
        if not res:
            res = {'status': 'error'}
        command = 'pack_is_updated' if res.get('status') == 'success' else 'pack_is_not_updated'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_pack(self, pack_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_pack(pack_id)
        if not res:
            res = {'status': 'error'}
        command = 'pack_is_deleted' if res.get('status') == 'success' else 'pack_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def get_classes(self, pack_id, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('classes', self.db_admin.get_classes(pack_id), recipient))

    async def create_class(self, pack_id, name, recipient):
        if not recipient:
            return
        res = self.db_admin.create_class(pack_id, name)
        if not res:
            res = {'status': 'error'}
        command = 'class_is_created' if res.get('status') == 'success' else 'class_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_class(self, pack_class_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_class(pack_class_id)
        if not res:
            res = {'status': 'error'}
        command = 'class_is_deleted' if res.get('status') == 'success' else 'class_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def get_commands(self, class_id, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('commands', self.db_admin.get_commands(class_id), recipient))

    async def create_command(self, class_id, name, recipient):
        if not recipient:
            return
        res = self.db_admin.create_command(class_id, name)
        if not res:
            res = {'status': 'error'}
        command = 'command_is_created' if res.get('status') == 'success' else 'command_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_command(self, class_command_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_command(class_command_id)
        if not res:
            res = {'status': 'error'}
        command = 'command_is_deleted' if res.get('status') == 'success' else 'command_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def get_roles(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('roles', self.db_admin.get_roles(), recipient))

    async def create_role(self, name, recipient):
        if not recipient:
            return
        res = self.db_admin.create_role(name)
        if not res:
            res = {'status': 'error'}
        command = 'role_is_created' if res.get('status') == 'success' else 'role_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def update_role(self, role_id, name, recipient):
        if not recipient:
            return
        res = self.db_admin.update_role(role_id, name)
        if not res:
            res = {'status': 'error'}
        command = 'role_is_updated' if res.get('status') == 'success' else 'role_is_not_updated'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_role(self, role_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_role(role_id)
        if not res:
            res = {'status': 'error'}
        command = 'role_is_deleted' if res.get('status') == 'success' else 'role_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def get_role_commands(self, role_id, recipient):
        if not recipient:
            return
        await self.adaptor.send(self.adaptor.get_msg('role_commands', self.db_admin.get_role_commands(role_id), recipient))

    async def create_role_command(self, role_id, command_id, recipient):
        if not recipient:
            return
        res = self.db_admin.create_role_command(role_id, command_id)
        if not res:
            res = {'status': 'error'}
        command = 'role_command_is_created' if res.get('status') == 'success' else 'role_command_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_role_command(self, role_command_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_role_command(role_command_id)
        if not res:
            res = {'status': 'error'}
        command = 'role_command_is_deleted' if res.get('status') == 'success' else 'role_command_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def get_users(self, recipient):
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('users', self.db_admin.get_users(), recipient))

    async def create_user(self, name, password, recipient):
        if not recipient:
            return
        res = self.db_admin.create_user(name, password)
        if not res:
            res = {'status': 'error'}
        command = 'user_is_created' if res.get('status') == 'success' else 'user_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def update_user(self, user_id, name, password, recipient):
        if not recipient:
            return
        res = self.db_admin.update_user(user_id, name, password)
        if not res:
            res = {'status': 'error'}
        command = 'user_is_updated' if res.get('status') == 'success' else 'user_is_not_updated'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_user(self, user_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_user(user_id)
        if not res:
            res = {'status': 'error'}
        command = 'user_is_deleted' if res.get('status') == 'success' else 'user_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def get_user_roles(self, user_id, recipient):
        if not recipient:
            return
        await self.adaptor.send(self.adaptor.get_msg('user_roles', self.db_admin.get_user_roles(user_id), recipient))

    async def create_user_role(self, user_id, role_id, recipient):
        if not recipient:
            return
        res = self.db_admin.create_user_role(user_id, role_id)
        if not res:
            res = {'status': 'error'}
        command = 'user_role_is_created' if res.get('status') == 'success' else 'user_role_is_not_created'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))

    async def delete_user_role(self, user_role_id, recipient):
        if not recipient:
            return
        res = self.db_admin.delete_user_role(user_role_id)
        if not res:
            res = {'status': 'error'}
        command = 'user_role_is_deleted' if res.get('status') == 'success' else 'user_role_is_not_deleted'
        await self.adaptor.send(self.adaptor.get_msg(command, res, recipient))
