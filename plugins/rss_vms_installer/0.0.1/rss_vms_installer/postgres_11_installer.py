import logging


class Stages:
    CHECK_STATUS = 0
    UPDATE_UPGRADE = 1
    WGET = 2


class Postgres11Installer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'postgres_install':
            await self.postgres_install(msg)
        else:
            return False
        return True

    async def postgres_install(self, msg):
        recipient = msg.get('sender')
        stage = Stages.CHECK_STATUS
        body = msg.get('body')
        if body and body.get('stage'):
            stage = body.get('stage')
        try:
            ans = await self._postgres_install(stage)
            if not ans:
                ans = self.adaptor.get_msg('postgres_is_not_installed')
            ans['recipient'] = recipient
            await self.adaptor.send(ans)
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('postgres_is_not_installed', recipient=recipient))

    async def _postgres_install(self, stage):
        if stage == Stages.CHECK_STATUS:
            res = await self.com_exe('service postgresql status')
            if res[0] == 0:
                logging.info('Postgres is already installed')
                res = await self.com_exe('apt-get --purge remove postgresql postgresql-* -y')
                if res[0] != 0:
                    return
                logging.info('Postgres is removed')
            stage = Stages.UPDATE_UPGRADE
        if stage == Stages.UPDATE_UPGRADE:
            res = await self.com_exe('apt update')
            if res[0] != 0:
                return
            res = await self.com_exe((['apt upgrade -y'], 1000))
            if res[0] != 0:
                return
            return self.adaptor.get_msg('need_to_reboot', {'stage': Stages.WGET})
        if stage == Stages.WGET:
            res = await self.com_exe('wget --version')
            if res[0] != 0:
                await self.com_exe('apt install -y wget')
            com = ['wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc', 'apt-key add -']
            res = await self.com_exe(com)
            if res[0] != 0:
                return
            res = await self.com_exe('lsb_release -cs')
            if res[0] != 0:
                return
            param = f'{res[1]}"-pgdg'
            if res[1] == 'focal':
                param += '-archive'
            com = [f'echo "deb https://apt-archive.postgresql.org/pub/repos/apt/ {param} main',
                   'tee /etc/apt/sources.list.d/pgdg.list']
            res = await self.com_exe(com)
            if res[0] != 0:
                return
            res = await self.com_exe('cat /etc/apt/sources.list.d/pgdg.list')
            if res[0] != 0:
                return
            res = await self.com_exe('apt update')
            if res[0] != 0:
                return
            res = await self.com_exe('apt -y install postgresql-11 postgresql-client-11')
            if res[0] != 0:
                return
            if not await self.adjust():
                return
            if not await self.set_password():
                return
            return self.adaptor.get_msg('postgres_is_installed')

    async def adjust(self):
        res = await self.com_exe('pg_config --version')
        if res[0] != 0:
            return False
        ver = res[1].split()[1].split('.')[0]
        postgresql_conf_path = f'/etc/postgresql/{ver}/main/postgresql.conf'
        with open(postgresql_conf_path, 'r') as file:
            lines = file.readlines()
        with open(postgresql_conf_path, 'w') as file:
            for line in lines:
                new_line = line.replace("#listen_addresses = 'localhost'", "listen_addresses = '*'")
                file.write(new_line)
        pg_hba_conf_path = f'/etc/postgresql/{ver}/main/pg_hba.conf'
        with open(pg_hba_conf_path, 'r') as file:
            lines = file.readlines()
        lines.append('host    all             all             0.0.0.0/0               md5\n')
        with open(pg_hba_conf_path, 'w') as file:
            file.writelines(lines)
        res = await self.com_exe('systemctl restart postgresql')
        return res[0] == 0

    async def set_password(self):
        # com = 'su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD \'adminadmin\';\\" "'
        lines = '''#!/bin/bash
        su - postgres << EOF
        psql -c "ALTER USER postgres WITH PASSWORD 'adminadmin';"
        EOF
        '''
        with open('set_password.sh', 'w') as file:
            for line in lines.split('\n'):
                file.write(line.strip() + '\n')
        await self.com_exe('chmod +x set_password.sh')
        res = await self.com_exe('./set_password.sh')
        await self.com_exe('rm set_password.sh')
        return res[0] == 0

    async def com_exe(self, coms):
        if isinstance(coms, str):
            coms = ([coms], 300)
        elif isinstance(coms, list):
            coms = (coms, 300)
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=coms)
        if len(res[1]) < 200 and len(res[2]) < 200:
            logging.debug(f'{coms}: {res}')
        else:
            res1 = res[1]
            res2 = res[2]
            if len(res1) > 200:
                res1 = res1[:200] + ' >>>>'
            if len(res2) > 200:
                res2 = res2[:200] + ' >>>>'
            logging.debug(f'{coms}: ({res[0]}, {res1}, {res2})')
        return res
