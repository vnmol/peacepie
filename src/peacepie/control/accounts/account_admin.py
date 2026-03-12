
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
