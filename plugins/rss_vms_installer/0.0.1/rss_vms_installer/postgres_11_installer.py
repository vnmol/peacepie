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
                return
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
            com = [f'echo "deb https://apt-archive.postgresql.org/pub/repos/apt/ {res[1]}"-pgdg-archive main',
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
            return self.adaptor.get_msg('postgres_is_installed')

    async def com_exe(self, coms):
        if isinstance(coms, str):
            coms = ([coms], 300)
        elif isinstance(coms, list):
            coms = (coms, 300)
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=coms)
        logging.debug(f'{coms}: {res}')
        return res
