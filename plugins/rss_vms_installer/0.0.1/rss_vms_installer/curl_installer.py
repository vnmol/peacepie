import logging


class CurlInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'curl_install':
            await self.curl_install(msg)
        else:
            return False
        return True

    async def curl_install(self, msg):
        recipient = msg.get('sender')
        try:
            await self._curl_install()
            await self.adaptor.send(self.adaptor.get_msg('curl_is_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('curl_is_not_installed', recipient=recipient))

    async def _curl_install(self):
        try:
            await self.adaptor.com_exe('curl --version')
            return
        except FileNotFoundError:
            pass
        await self.adaptor.com_exe('apt-get update')
        await self.adaptor.com_exe('apt-get install curl -y')
