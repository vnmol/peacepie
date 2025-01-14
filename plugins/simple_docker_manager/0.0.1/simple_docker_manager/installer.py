import getpass
import logging
import os

from docker import from_env


class SimpleDockerInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else None
        sender = msg.get('sender')
        if command == 'install':
            await self.install(sender)
        else:
            return False
        return True

    async def install(self, recipient):
        is_normal = False
        if await self.is_installed():
            if await self.is_connected():
                is_normal = True
        if recipient:
            if is_normal:
                await self.adaptor.send(self.adaptor.get_msg('docker_is_installed', None, recipient))
            else:
                await self.adaptor.send(self.adaptor.get_msg('docker_is_not_installed', None, recipient))

    async def is_installed(self):
        try:
            await self.adaptor.com_exe('docker --version')
            logging.info('Docker is found')
            return True
        except FileNotFoundError:
            logging.info('Docker is not found')
        return await self.adaptor.sudo_com_exe('sudo', 'apt install -y docker.io')

    async def is_connected(self):
        res = self.check_connection()
        if res is not None:
            return res
        res = await self.check_group()
        if res is False:
            return res
        if res is None:
            await self.adaptor.sudo_com_exe('sudo', 'groupadd docker')
        if not await self.check_user_in_group():
            return False
        res = self.check_connection()
        if res is None:
            res = False
        return res

    def check_connection(self):
        try:
            client = from_env()
            logging.info(client.info())
            client.close()
            return True
        except Exception as e:
            if "PermissionError(13, 'Permission denied')".lower() in str(e).lower():
                return None
            else:
                logging.exception(e)
                return False

    async def check_group(self):
        try:
            await self.adaptor.com_exe('getent group docker')
            return True
        except Exception as e:
            if isinstance(e, Exception):
                return None
            else:
                logging.exception(e)
                return False

    async def check_user_in_group(self):
        username = getpass.getuser()
        try:
            res = await self.adaptor.com_exe('getent group docker')
            if username not in res[1].split(":")[-1].split(","):
                await self.adaptor.sudo_com_exe('sudo', f'usermod -aG docker {username}')
                await self.adaptor.sudo_com_exe('sudo', f'systemctl restart docker')
            return True
        except Exception as e:
            logging.exception(e)
            return False
