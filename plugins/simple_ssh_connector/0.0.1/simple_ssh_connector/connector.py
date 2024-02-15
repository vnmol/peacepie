import logging

import asyncssh


class SimpleSshConnector:

    def __init__(self):
        self.adaptor = None
        self.connection = None
        self.listener = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'ssh_connect':
            await self.ssh_connect(msg)
        else:
            return False
        return True

    async def ssh_connect(self, msg):
        desc = msg.get('body')
        if not desc:
            await self.adaptor.send(self.adaptor.get_msg('not_connected', recipient=msg.get('sender')))
            return
        try:
            self.connection = await asyncssh.connect(
                desc.get('host'), desc.get('ssh_port'), username=desc.get('username'),
                client_keys=[f'{desc.get("key_dir")}/{desc.get("key_name")}'], passphrase=desc.get('passphrase'))
            logging.info('Connected to host "' + desc.get('host') + '" by ssh')
            self.listener = await self.connection.forward_local_port('', 0, desc.get('host'), desc.get('port'))
            port = self.listener.get_port()
            logging.info(f'The port {port} is forwarded to {desc.get("host")}:{desc.get("port")}')
            await self.adaptor.send(self.adaptor.get_msg('ssh_connected', {'port': port}, msg.get('sender')))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('not_ssh_connected', recipient=msg.get('sender')))
            if self.adaptor.get_param('developing_mode'):
                self.upload_keys(desc)

    def upload_keys(self, desc):
        cmd = f'sshpass -p adminadmin ssh-copy-id -o StrictHostKeyChecking=no -i {desc.get("key_dir")}/{desc.get("key_name")}'
        cmd += f' -p {desc.get("ssh_port")} {desc.get("username")}@{desc.get("host")}'
        res = self.adaptor.execute(cmd)
        if res[0] == 0:
            log = f'{self.adaptor.get_alias(self)} The keys is added to remote server "{desc.get("host")}" with result: "{res[1]}"'
            logging.info(log)
            return True
        else:
            log = f'{self.adaptor.get_alias(self)} The keys is not added to remote server "{desc.get("host")}" with result: "{res[2]}"'
            logging.warning(log)
            return False
