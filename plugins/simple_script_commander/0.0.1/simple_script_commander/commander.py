import logging
import os
import asyncssh

KEY_DIR = '.ssh'
PASSPHRASE = 'qwerty'

SERVICE_SOURCE = 'peacepie_service'
SERVICE_DESTINATION = 'opt/peacepie_service'
SERVICE_NAME = 'peacepie_service.pyz'
SERVICE_CONFIG = 'peacepie.service'
SERVICE_CONFIG_DEST = '/etc/systemd/system'

LOG_CONFIG_NAME = 'log.cfg'



class SimpleScriptCommander:

    def __init__(self):
        self.adaptor = None
        self.check_keys(KEY_DIR, PASSPHRASE)
        self.servers = {}

    def check_keys(self, key_dir, passphrase):
        # f'ssh-keygen -f {KEY_DIR}/id_rsa -N {passphrase}'
        if not os.path.isdir(key_dir):
            os.mkdir(key_dir)
        if os.path.isfile(f'{key_dir}/id_rsa') and os.path.isfile(f'{key_dir}/id_rsa.pub'):
            return
        private_key = asyncssh .generate_private_key('ssh-rsa')
        private_key.write_private_key(f'{key_dir}/id_rsa', passphrase=passphrase)
        private_key.write_public_key(f'{key_dir}/id_rsa.pub')

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'add_server':
            await self.add_server(msg)
        else:
            return False
        return True

    async def add_server(self, msg):
        body = msg.get('body')
        if not body:
            return
        host = body.get('host')
        port = body.get('port')
        username = body.get('username')
        password = body.get('password')
        if self.servers.get(host):
            return
        if not self.copy_keys_to_server(username, password, host, port):
            return
        await self.upload(host, port, username, password)
        print('SERVER_IS_ADDED')

    def copy_keys_to_server(self, username, password, host, port=22):
        cmd = f'sshpass -p {password} ssh-copy-id -o StrictHostKeyChecking=no -i {KEY_DIR}/id_rsa -p {port}'
        cmd += f' {username}@{host}'
        res = self.adaptor.execute(cmd)
        log = f'{self.adaptor.get_alias(self)}'
        if res[0] == 0:
            self.servers[host] = {'port': port, 'username': username}
            log += f' The keys is added to remote server "{host}" with result: "{res[1]}"'
            logging.info(log)
            return True
        else:
            log += f' The keys is not added to remote server "{host}" with result: "{res[2]}"'
            logging.warning(log)
            return False

    async def upload(self, host, port, username, password):
        async with asyncssh.connect(host, port, username=username, client_keys=[f'{KEY_DIR}/id_rsa'],
                                    passphrase=PASSPHRASE) as conn:
            result = await conn.run(f'mkdir -p {SERVICE_DESTINATION}')
            if result.exit_status != 0:
                return
            async with conn.start_sftp_client() as sftp:
                await sftp.put(f'{SERVICE_SOURCE}/{SERVICE_NAME}', f'{SERVICE_DESTINATION}/{SERVICE_NAME}')
                await sftp.put(f'{SERVICE_SOURCE}/{LOG_CONFIG_NAME}', f'{SERVICE_DESTINATION}/{LOG_CONFIG_NAME}')
                self.form_systemd(username)
                await sftp.put(f'{SERVICE_SOURCE}/{SERVICE_CONFIG}', f'{SERVICE_DESTINATION}/{SERVICE_CONFIG}')
            cmd = f'sudo -S <<< "{password}" cp {SERVICE_DESTINATION}/{SERVICE_CONFIG}'
            cmd += f' {SERVICE_CONFIG_DEST}/{SERVICE_CONFIG}'
            await conn.run(cmd)
            await conn.run(f'sudo -S <<< "{password}" systemctl daemon-reload')
            await conn.run(f'sudo -S <<< "{password}" systemctl enable {SERVICE_CONFIG}')
            await conn.run(f'sudo -S <<< "{password}" systemctl start {SERVICE_CONFIG}')

    def form_systemd(self, username):
        res = '[Unit]\r\n'
        res += 'Description=peacepie_service\r\n'
        res += 'After=multi-user.target\r\n'
        res += '[Service]\r\n'
        res += 'Type=simple\r\n'
        res += 'Restart=always\r\n'
        res += f'ExecStart=/usr/bin/python3 /home/{username}/{SERVICE_DESTINATION}/{SERVICE_NAME}\r\n'
        res += '[Install]\r\n'
        res += 'WantedBy=multi-user.target\r\n'
        with open(f'{SERVICE_SOURCE}/{SERVICE_CONFIG}', 'w') as f:
            f.write(res)
