import logging


class OpenJdkJava8Installer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'java_install':
            await self.java_install(msg)
        else:
            return False
        return True

    async def java_install(self, msg):
        try:
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args='java -version')
            logging.debug(f'java_version_result: {res}')
            return
        except FileNotFoundError:
            logging.debug(f'Java not found')
        except Exception as e:
            logging.exception(e)
            return
        try:
            command = 'add-apt-repository ppa:openjdk-r/ppa'
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=(command, 300))
            logging.debug(f'add-apt-repository: {res}')
        except Exception as e:
            logging.exception(e)
            return
        try:
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=('apt-get update', 300))
            logging.debug(f'apt-get update: {res}')
        except Exception as e:
            logging.exception(e)
            return
        try:
            command = 'apt-get install -y openjdk-8-jdk'
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=(command, 300))
            logging.debug(f'apt-get install openjdk-8-jdk: {res}')
        except Exception as e:
            logging.exception(e)
