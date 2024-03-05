import logging


class Utf8RuLocaleInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'ru_install':
            await self.ru_install()
        else:
            return False
        return True

    async def ru_install(self):
        try:
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args='locale')
            logging.debug(f'locale: {res}')
            if b'LANG=ru_RU.UTF-8' in res[1]:
                logging.info('The locale ru_RU is already installed')
                return
        except Exception as e:
            logging.exception(e)
            return
        try:
            command = 'apt-get install -y language-pack-ru'
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=(command, 300))
            logging.debug(f'apt-get install language-pack-ru: {res}')
        except Exception as e:
            logging.exception(e)
            return
        try:
            command = 'update-locale LANG=ru_RU.UTF-8 LANGUAGE=ru_RU:ru'
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=(command, 300))
            logging.debug(f'update-locale LANG=ru_RU.UTF-8 LANGUAGE=ru_RU:ru: {res}')
        except Exception as e:
            logging.exception(e)
        try:
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=('reboot now', 300))
            logging.debug(f'reboot: {res}')
        except Exception as e:
            logging.exception(e)
