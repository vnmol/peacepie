import logging


class Utf8RuLocaleInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'ru_install':
            await self.ru_install(msg.get('sender'))
        else:
            return False
        return True

    async def ru_install(self, recipient):
        try:
            ans = await self._ru_install()
            if not ans:
                ans = self.adaptor.get_msg('ru_is_installed')
            ans['recipient'] = recipient
            await self.adaptor.send(ans)
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('ru_is_not_installed', recipient=recipient))

    async def _ru_install(self):
        com = 'locale'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=com)
        logging.debug(f'{com}: {res}')
        if 'LANG=ru_RU.UTF-8' in res[1]:
            logging.info('The locale ru_RU is already installed')
            return
        com = 'apt-get install -y language-pack-ru'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=([com], 300))
        logging.debug(f'{com}: {res}')
        com = 'update-locale LANG=ru_RU.UTF-8 LANGUAGE=ru_RU:ru'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=([com], 300))
        logging.debug(f'{com}: {res}')
        return self.adaptor.get_msg('need_to_reboot', {'stage': None})
