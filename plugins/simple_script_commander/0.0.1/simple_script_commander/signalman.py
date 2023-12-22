import logging
import os

import asyncssh

KEY_DIR = '.ssh'
KEY_NAME = 'id_rsa'
PASSPHRASE = 'qwerty'

SERVER_LIST_DIR = None
SERVER_LIST_NAME = 'signalman.cfg'

SYSTEM_NAME = 'system_name'
HOST = 'host'
PORT = 'port'
SSH_PORT = 'ssh_port'
USERNAME = 'username'
PASSWORD = 'password'

CONFIG_NAME = 'peacepie.cfg'
LOG_CONFIG_NAME = 'log.cfg'

SERVICE_SOURCE = 'peacepie_service'
SERVICE_DESTINATION = 'opt/peacepie_service'
SERVICE_NAME = 'peacepie_service.pyz'
SERVICE_CONFIG = 'peacepie.service'
SERVICE_CONFIG_DEST = '/etc/systemd/system'

SSH_CONN = 'ssh_conn'
LISTENER = 'listener'


def check_keys():
    if not os.path.isdir(KEY_DIR):
        os.mkdir(KEY_DIR)
    if os.path.isfile(f'{KEY_DIR}/{KEY_NAME}') and os.path.isfile(f'{KEY_DIR}/{KEY_NAME}.pub'):
        return
    private_key = asyncssh.generate_private_key('ssh-rsa')
    private_key.write_private_key(f'{KEY_DIR}/{KEY_NAME}', passphrase=PASSPHRASE)
    private_key.write_public_key(f'{KEY_DIR}/{KEY_NAME}.pub')


class Signalman:

    def __init__(self, parent):
        self.parent = parent
        self.servers = {}
        self.connections = {}
        self.listeners = {}
        check_keys()
        self.load_config()
        self.alias = self.parent.adaptor.get_alias(self)
        logging.info(f'{self.alias} is created')

    def check_dir(self, dir_name, file_name):
        if dir_name and dir_name != '':
            if not os.path.isdir(dir_name):
                os.mkdir(dir_name)
            return f'{dir_name}/{file_name}'
        else:
            return file_name

    def load_config(self):
        file_name = self.check_dir(SERVER_LIST_DIR, SERVER_LIST_NAME)
        try:
            with open(file_name) as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    try:
                        desc = self.parent.adaptor.json_loads(line)
                        self.servers[desc.get(SYSTEM_NAME)] = desc
                    except Exception as e:
                        logging.exception(e)
        except Exception as ex:
            logging.exception(ex)

    def save_config(self):
        file_name = self.check_dir(SERVER_LIST_DIR, SERVER_LIST_NAME)
        with open(file_name, 'w') as f:
            for server in self.servers.values():
                f.write(self.parent.adaptor.json_dumps(server))

    async def add_server(self, msg):
        desc = msg.get('body')
        if self.servers.get(desc.get(SYSTEM_NAME)):
            logging.info(f'The server "{desc.get(SYSTEM_NAME)}" is already exist')
            return
        self.upload_keys(desc)
        if not await self._connect(desc):
            return
        if not await self.upload(desc):
            return
        if not await self.create_venv(desc):
            return
        if not await self.start_service(desc):
            return
        ans = self.parent.adaptor.get_msg('server_is_added', f'The server "{desc.get(SYSTEM_NAME)}" is added',
                                          msg.get('sender'))
        await self.parent.adaptor.send(ans)

    def upload_keys(self, desc):
        cmd = f'sshpass -p {desc.get(PASSWORD)} ssh-copy-id -o StrictHostKeyChecking=no -i {KEY_DIR}/{KEY_NAME}'
        cmd += f' -p {desc.get(SSH_PORT)} {desc.get(USERNAME)}@{desc.get(HOST)}'
        res = self.parent.adaptor.execute(cmd)
        if res[0] == 0:
            log = f'{self.alias} The keys is added to remote server "{desc.get(HOST)}" with result: "{res[1]}"'
            logging.info(log)
            return True
        else:
            log = f'{self.alias} The keys is not added to remote server "{desc.get(HOST)}" with result: "{res[2]}"'
            logging.warning(log)
            return False

    async def _connect(self, desc):
        try:
            conn = await asyncssh.connect(desc.get(HOST), desc.get(SSH_PORT), username=desc.get(USERNAME),
                                          client_keys=[f'{KEY_DIR}/{KEY_NAME}'], passphrase=PASSPHRASE)
            self.connections[desc.get(SYSTEM_NAME)] = conn
            logging.info(f'Connected to system "{desc.get(SYSTEM_NAME)}" by ssh')
        except Exception as e:
            logging.exception(e)
            return False
        return True

    async def _disconnect(self, system_name):
        listener = self.listeners.get(system_name)
        if listener:
            listener.close()
            await listener.wait_closed()
            del self.listeners[system_name]
        conn = self.connections.get(system_name)
        if conn:
            conn.close()
            await conn.wait_closed()
            del self.connections[system_name]
            logging.info(f'Disconnected from system "{system_name}" by ssh')

    async def upload(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        result = await conn.run(f'mkdir -p {SERVICE_DESTINATION}')
        if result.exit_status != 0:
            logging.warning('Unable to create an application folder')
            return False
        async with conn.start_sftp_client() as sftp:
            await sftp.put(f'{SERVICE_SOURCE}/{SERVICE_NAME}', f'{SERVICE_DESTINATION}/{SERVICE_NAME}')
            await sftp.put(f'{SERVICE_SOURCE}/{LOG_CONFIG_NAME}', f'{SERVICE_DESTINATION}/{LOG_CONFIG_NAME}')
            self.form_systemd(desc.get(USERNAME))
            await sftp.put(f'{SERVICE_SOURCE}/{SERVICE_CONFIG}', f'{SERVICE_DESTINATION}/{SERVICE_CONFIG}')
            self.form_config(desc.get(SYSTEM_NAME), desc.get(PORT))
            await sftp.put(f'{SERVICE_SOURCE}/{CONFIG_NAME}', f'{SERVICE_DESTINATION}/{CONFIG_NAME}')
        cmd = f'sudo -S <<< "{desc[PASSWORD]}" cp {SERVICE_DESTINATION}/{SERVICE_CONFIG}'
        cmd += f' {SERVICE_CONFIG_DEST}/{SERVICE_CONFIG}'
        await conn.run(cmd)
        return True

    def form_systemd(self, username):
        res = '[Unit]\r\n'
        res += 'Description=peacepie_service\r\n'
        res += 'After=network.target\r\n'
        res += '[Service]\r\n'
        res += 'Type=simple\r\n'
        res += 'Restart=always\r\n'
        res += 'RestartSec = 10s\r\n'
        res += f'WorkingDirectory=/home/{username}/{SERVICE_DESTINATION}\r\n'
        res += f'ExecStart=/home/{username}/{SERVICE_DESTINATION}/venv/bin/python '
        res += f'/home/{username}/{SERVICE_DESTINATION}/{SERVICE_NAME} {CONFIG_NAME}\r\n'
        res += f'StandardOutput = file:/home/{username}/{SERVICE_DESTINATION}/output.log\r\n'
        res += f'StandardError = file:/home/{username}/{SERVICE_DESTINATION}/error.log\r\n'
        res += '[Install]\r\n'
        res += 'WantedBy=multi-user.target\r\n'
        with open(f'{SERVICE_SOURCE}/{SERVICE_CONFIG}', 'w') as f:
            f.write(res)

    def form_config(self, system_name, port):
        res = f'log_config={LOG_CONFIG_NAME}\r\n'
        res += f'system_name={system_name}\r\n'
        res += f'host_name=host\r\n'
        res += f'process_name=main\r\n'
        res += f'intra_role=master\r\n'
        res += f'intra_host=localhost\r\n'
        res += f'intra_port=0\r\n'
        res += f'inter_port={port}\r\n'
        res += f'extra-index-url=https://test.pypi.org/simple/\r\n'
        res += f'package_dir=packages\r\n'
        res += f'starter=None\r\n'
        res += f'start_command=None\r\n'
        with open(f'{SERVICE_SOURCE}/{CONFIG_NAME}', 'w') as f:
            f.write(res)

    async def create_venv(self, desc):
        system_name = desc.get(SYSTEM_NAME)
        conn = self.connections.get(system_name)
        if not conn:
            return False
        await conn.run(f'python3 -m venv {SERVICE_DESTINATION}/venv')
        await conn.run(f'source {SERVICE_DESTINATION}/venv/bin/activate')
        return True

    async def start_service(self, desc):
        system_name = desc.get(SYSTEM_NAME)
        password = desc.get(PASSWORD)
        conn = self.connections.get(system_name)
        if not conn:
            return False
        await conn.run(f'sudo -S <<< "{password}" systemctl daemon-reload')
        await conn.run(f'sudo -S <<< "{password}" systemctl enable {SERVICE_CONFIG}')
        await conn.run(f'sudo -S <<< "{password}" systemctl start {SERVICE_CONFIG}')
        await self._disconnect(system_name)
        self.servers[desc.get(SYSTEM_NAME)] = desc
        self.save_config()
        logging.info(f'{self.alias} The remote service "{system_name}" is started')
        return True

    async def connect(self, msg):
        desc = msg.get('body')
        if not desc:
            logging.warning(f'Wrong format of message "{msg}"')
            return None
        system_name = desc.get(SYSTEM_NAME)
        if not system_name:
            logging.warning(f'Can\'t find a system_name in message "{msg}"')
            return None
        conn = self.connections.get(system_name)
        if not conn:
            desc = self.servers.get(system_name)
            if not desc:
                logging.warning(f'There is no description for system "{system_name}"')
                return None
            if not await self._connect(desc):
                logging.warning(f'Unable connect to system "{system_name}"')
                return None
            conn = self.connections.get(system_name)
        listener = self.listeners.get(system_name)
        if not listener:
            listener = await conn.forward_local_port('', 0, desc.get(HOST), desc.get(PORT))
            self.listeners[system_name] = listener
            logging.info(f'The port {listener.get_port()} is forwarded to {desc.get(HOST)}:{desc.get(PORT)}')
        return listener.get_port()

    async def disconnect(self, msg):
        body = msg.get('body')
        if not body:
            return
        await self._disconnect(body.get('system_name'))
