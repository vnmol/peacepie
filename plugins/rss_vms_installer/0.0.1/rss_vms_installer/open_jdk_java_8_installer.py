import logging


class OpenJdkJava8Installer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'java_install':
            await self.java_install(msg.get('sender'))
        else:
            return False
        return True

    async def java_install(self, recipient):
        try:
            await self._java_install()
            await self.adaptor.send(self.adaptor.get_msg('java_is_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('java_is_not_installed', recipient=recipient))

    async def _java_install(self):
        try:
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args='java -version')
            logging.debug(f'java_version_result: {res}')
            return
        except FileNotFoundError:
            logging.debug(f'Java not found')
        com = 'add-apt-repository ppa:openjdk-r/ppa'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=(com, 300))
        logging.debug(f'add-apt-repository: {res}')
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=('apt-get update', 300))
        logging.debug(f'apt-get update: {res}')
        com = 'apt-get install -y openjdk-8-jdk'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=(com, 300))
        logging.debug(f'apt-get install openjdk-8-jdk: {res}')
