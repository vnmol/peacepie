import logging

from peacepie.control.accounts.password_hasher import PasswordHasher


class AccountAdmin:

    def __init__(self):
        self.adaptor = None
        self.roles = None
        self.pack_names = None
        self.class_names = None
        self.command_names = None
        self.permissions = None
        self.role_permissions = None
        self.users = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'start':
            await self.start(sender)
        elif command == 'login':
            await self.login(body, sender)
        else:
            return False
        return True

    async def start(self, recipient):
        msg = self.adaptor.get_msg('get_credentials', {'credentials_name': 'account_admin'})
        ans = await self.adaptor.ask(msg)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        password_hash = PasswordHasher.hash_password(body.get('password'))
        self.roles = {1: 'system', 'is_builtin': True}
        self.pack_names = {1: '*'}
        self.class_names = {1: '*'}
        self.command_names = {1: '*'}
        self.role_permissions = {1: {1: {1: {1}}}} # {role: {pack: {class: [command_1, ..., command_N]}}}
        self.users = {body.get('username'): {'is_builtin': True, 'password_hash': password_hash, 'roles': {1}}}
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', None, recipient))

    async def login(self, body, recipient):
        command = 'is_not_logged'
        try:
            if PasswordHasher.verify_password(
                    body.get('password'), self.users.get(body.get('username')).get('password_hash')):
                command = 'is_logged'
        except Exception as e:
            logging.exception(e)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg(command, None, recipient))



def str_to_tuple(key):
    key = key.strip('()')
    if not key:
        return None
    parts = [part.strip() for part in key.split(',')]
    res = []
    for part in parts:
        if part.isdigit():
            res.append(int(part))
        else:
            return None
    if res:
        return tuple(res)
    return None


def transform(data):
    if not isinstance(data, dict):
        return None
    res = {}
    for key, val in data.items():
        new_key = key
        if isinstance(key, str):
            if key.isdigit():
                new_key = int(key)
            else:
                k = str_to_tuple(key)
                if k:
                    new_key = k
        new_val = val
        if isinstance(val, list):
            new_val = set(val)
        elif isinstance(val, dict):
            new_val = transform(val)
        res[new_key] = new_val
    return res
