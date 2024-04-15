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
            await self.com_exe('java -version')
            return
        except FileNotFoundError:
            logging.debug(f'Java not found')
        await self.com_exe('add-apt-repository ppa:openjdk-r/ppa')
        await self.com_exe('apt-get update')
        await self.com_exe('apt-get install -y openjdk-8-jdk')

    async def com_exe(self, coms, timeout=300):
        if isinstance(coms, str):
            coms = ([coms], timeout)
        elif isinstance(coms, list):
            coms = (coms, timeout)
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
