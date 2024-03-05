import logging


class Postgres11Installer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'postgres_install':
            await self.postgres_install()
        else:
            return False
        return True

    async def postgres_install(self):
        try:
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args='service postgresql status')
            logging.debug(f'service postgresql status: {res}')
            if res[0] == 0:
                logging.info('Postgres is already installed')
                return
        except Exception as e:
            logging.exception(e)
            return
        try:
            command = 'apt update && apt -y upgrade'
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=command)
            logging.debug(f'service postgresql status: {res}')
            if res[0] == 0:
                logging.info('Postgres is already installed')
                return
        except Exception as e:
            logging.exception(e)
            return
