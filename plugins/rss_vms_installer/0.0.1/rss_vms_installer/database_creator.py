import logging


class DatabaseCreator:
    
    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'create_database':
            await self.create_database(msg)
        else:
            return False
        return True

    async def create_database(self, msg):
        recipient = msg.get('sender')
        try:
            await self._create_database()
            await self.adaptor.send(self.adaptor.get_msg('database_is_created', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('database_is_not_created', recipient=recipient))

    async def _create_database(self):
        # com = 'su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD \'adminadmin\';\\" "'
        admin_name = 'postgres'
        res = await self.get_credentials(admin_name)
        admin_password = res.get('password')
        user_name = 'vms'
        res = await self.get_credentials(user_name)
        user_password = res.get('password')
        lines = '#!/bin/bash\n'
        lines += f'su - {admin_name} << EOF\n'
        lines += f'psql -c "ALTER USER {admin_name} WITH PASSWORD \'{admin_password}\';"\n'
        lines += f'psql -c "CREATE USER {user_name} WITH SUPERUSER PASSWORD \'{user_password}\';"\n'
        lines += f'createdb -E UTF8 -O {user_name} vms_ws\n'
        lines += 'EOF\n'
        with open('create_database.sh', 'w') as file:
            for line in lines.split('\n'):
                file.write(line.strip() + '\n')
        await self.adaptor.com_exe('chmod +x create_database.sh')
        res = await self.adaptor.com_exe('./create_database.sh')
        await self.adaptor.com_exe('rm create_database.sh')

    async def get_credentials(self, credentials_name):
        body = {'credentials_name': credentials_name}
        query = self.adaptor.get_msg('get_credentials', body, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        return body
