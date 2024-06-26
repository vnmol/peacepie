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
EXTRA_INDEX_URL = 'extra-index-url'
SSH_PORT = 'ssh_port'
USERNAME = 'username'
PASSWORD = 'password'

PY_VERSION = '3.10.12'

CONFIG_NAME = 'peacepie.cfg'
APP_STARTER = 'app_starter.py'
LOG_CONFIG_NAME = 'log.cfg'
SAFE_CONFIG_NAME = 'safe.cfg'

SERVICE_SOURCE = 'peacepie_service'
COMPILE = 'compile.sh'
SERVICE_DESTINATION = '/opt/' + SERVICE_SOURCE
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
        # self.load_config()
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
        flag = True
        if self.servers.get(desc.get(SYSTEM_NAME)):
            logging.info(f'The server "{desc.get(SYSTEM_NAME)}" is already exist')
            return
        if not await self.upload_keys(desc):
            flag = False
        if flag and not await self._connect(desc):
            flag = False
        if flag and not await self.set_timezone(desc):
            flag = False
        if flag and not await self.edit_source_list(desc):
            flag = False
        if flag and not await self.install_software_properties_common(desc):
            flag = False
        if not await self.install_python_from_source_code(desc):
            flag = False
        if flag and not await self.install_venv(desc):
            flag = False
        if flag and not await self.upload(desc):
            flag = False
        if flag and not await self.create_venv(desc):
            flag = False
        if flag and not await self.start_service(desc):
            flag = False
        if flag:
            body = f'The server "{desc.get(SYSTEM_NAME)}" is added'
            ans = self.parent.adaptor.get_msg('server_is_added', body, msg.get('sender'))
        else:
            body = f'The server "{desc.get(SYSTEM_NAME)}" is not added'
            ans = self.parent.adaptor.get_msg('server_is_not_added', body, msg.get('sender'))
        await self.parent.adaptor.send(ans)

    async def server_is_not_added(self, system_name, recipient):
        ans = self.parent.adaptor.get_msg('server_is_not_added', f'The server "{system_name}" is not added', recipient)
        await self.parent.adaptor.send(ans)

    async def upload_keys(self, desc):
        cmd = f'sshpass -p {desc.get(PASSWORD)} ssh-copy-id -o StrictHostKeyChecking=no -i {KEY_DIR}/{KEY_NAME}'
        cmd += f' -p {desc.get(SSH_PORT)} {desc.get(USERNAME)}@{desc.get(HOST)}'
        try:
            res = await self.parent.adaptor.sync_as_async(self.parent.adaptor.execute, sync_args=([cmd], 60))
            log = f'{self.alias} The keys is added to remote server "{desc.get(HOST)}" with result: "{res}"'
            logging.info(log)
            return True
        except Exception as e:
            logging.exception(e)
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

    async def set_timezone(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        result = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' timedatectl set-timezone Europe/Moscow")
        if result.exit_status != 0:
            logging.warning('Unable to set timezone: ' + result.stdout)
            return False
        return True

    async def edit_source_list(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        result = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' sed -i '/^deb cdrom:/s/^/#/' /etc/apt/sources.list")
        if result.exit_status != 0:
            logging.warning('Unable to sed: ' + result.stdout)
            return False
        return True

    async def install_software_properties_common(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        res = await conn.run(f'sudo -S <<< "{desc[PASSWORD]}" apt-get install software-properties-common -y')
        if res.exit_status != 0:
            logging.warning('Unable to install software-properties-common: ' + res.stdout)
            return False
        return True

    async def install_python_from_deadsnakes(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        result = await conn.run(f'sudo -S <<< "{desc[PASSWORD]}" add-apt-repository ppa:deadsnakes/ppa')
        if result.exit_status != 0:
            logging.warning('Unable to add-apt-repository: ' + result.stdout)
            return False
        result = await conn.run(f'sudo -S <<< "{desc[PASSWORD]}" apt-get update')
        if result.exit_status != 0:
            logging.warning('Unable to update: ' + result.stdout)
            return False
        result = await conn.run(f'sudo -S <<< "{desc[PASSWORD]}" apt-get install -y python3.10')
        if result.exit_status != 0:
            logging.warning('Unable to install python3.10: ' + result.stdout)
            return False
        result = await conn.run(f'python3.10 --version')
        if result.exit_status != 0:
            logging.warning(f'Python3.10 is not found: {result}')
            return False
        return True

    async def install_python_from_source_code(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        res = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' apt-get update")
        if res.exit_status != 0:
            logging.warning(f'Unable to update: {res}')
            return False
        command = f"sudo -S <<< '{desc[PASSWORD]}' apt install -y build-essential zlib1g-dev libncurses5-dev"
        command += ' libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget'
        res = await conn.run(command)
        if res.exit_status != 0:
            logging.warning(f'Unable to install essentials: {res}')
            return False
        res = await conn.run(f'mkdir -p tmp')
        if res.exit_status != 0:
            logging.warning(f'Unable to create an tmp folder: {res}')
            return False
        res = await conn.run(f'wget -P ./tmp/ https://python.org/ftp/python/{PY_VERSION}/Python-{PY_VERSION}.tgz')
        if res.exit_status != 0:
            logging.warning(f'Unable to load python archive: {res}')
            await self.compile_cleaning(conn, desc)
            return False
        res = await conn.run(f'tar -xf ./tmp/Python-{PY_VERSION}.tgz -C ./tmp')
        if res.exit_status != 0:
            logging.warning(f'Unable to unzip python archive: {res}')
            await self.compile_cleaning(conn, desc)
            return False
        nproc = 1
        res = await conn.run('nproc --all')
        if res.exit_status == 0:
            nproc = int(res.stdout)
        else:
            logging.warning(f'Unable to get a number of cores: {res}')
        self.form_python_bash(nproc)
        async with conn.start_sftp_client() as sftp:
            await sftp.put(f'{SERVICE_SOURCE}/{COMPILE}', f'{COMPILE}')
        os.remove(f'{SERVICE_SOURCE}/{COMPILE}')
        res = await conn.run(f'chmod +x {COMPILE}')
        if res.exit_status != 0:
            logging.warning(f'Unable to execute chmod: {res}')
            await self.compile_cleaning(conn, desc)
            return False
        res = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' ./{COMPILE}")
        if res.exit_status != 0:
            logging.warning(f'Unable to execute "compile.sh": {res}')
            await self.compile_cleaning(conn, desc)
            return False
        await self.compile_cleaning(conn, desc)
        return True

    async def compile_cleaning(self, conn, desc):
        try:
            res = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' rm -r tmp")
            res = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' rm {COMPILE}")
        except Exception as e:
            logging.exception('cleaning error', e)

    def form_python_bash(self, nproc):
        res = '#!/bin/bash\n'
        res += f'cd ./tmp/Python-{PY_VERSION}\n'
        res += './configure --enable-optimizations\n'
        if nproc > 0:
            res += f'make -j {nproc}\n'
        res += 'make altinstall\n'
        with open(f'{SERVICE_SOURCE}/{COMPILE}', 'w') as f:
            f.write(res)

    async def install_venv(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        res = await conn.run('python3 -m venv --help')
        if res.exit_status == 0:
            return True
        res = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' apt-get update")
        if res.exit_status != 0:
            logging.warning('Unable to update: ' + res.stdout)
            return False
        res = await conn.run(f'sudo -S <<< "{desc[PASSWORD]}" apt install python3.10-venv python3.10-dev -y')
        if res.exit_status != 0:
            logging.warning('Unable to install venv: ' + res.stdout)
            return False
        return True

    async def upload(self, desc):
        conn = self.connections.get(desc.get(SYSTEM_NAME))
        if not conn:
            return False
        self.form_systemd(desc.get(USERNAME))
        self.form_config(desc.get(SYSTEM_NAME), desc.get(PORT), desc.get(EXTRA_INDEX_URL))
        async with conn.start_sftp_client() as sftp:
            await sftp.put(SERVICE_SOURCE, SERVICE_SOURCE, recurse=True)
        src = f'{SERVICE_SOURCE}/{SERVICE_CONFIG}'
        dst = f'{SERVICE_CONFIG_DEST}/{SERVICE_CONFIG}'
        await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' mv {src} {dst}")
        await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' mv {SERVICE_SOURCE} {SERVICE_DESTINATION}")
        return True

    def form_systemd(self, username):
        res = '[Unit]\r\n'
        res += 'Description=peacepie_service\r\n'
        res += 'After=network.target\r\n'
        res += '[Service]\r\n'
        res += 'Type=simple\r\n'
        res += 'Restart=always\r\n'
        res += 'RestartSec = 10s\r\n'
        res += f'WorkingDirectory={SERVICE_DESTINATION}\r\n'
        res += f'ExecStart={SERVICE_DESTINATION}/venv/bin/python3.10 '
        res += f'{SERVICE_DESTINATION}/{SERVICE_NAME} {CONFIG_NAME}\r\n'
        res += f'StandardOutput = file:{SERVICE_DESTINATION}/output.log\r\n'
        res += f'StandardError = file:{SERVICE_DESTINATION}/error.log\r\n'
        res += '[Install]\r\n'
        res += 'WantedBy=multi-user.target\r\n'
        with open(f'{SERVICE_SOURCE}/{SERVICE_CONFIG}', 'w') as f:
            f.write(res)

    def form_config(self, system_name, port, extra_index_url):
        res = f'log_config={LOG_CONFIG_NAME}\r\n'
        res += f'safe_config={SAFE_CONFIG_NAME}\r\n'
        res += f'system_name={system_name}\r\n'
        res += f'host_name=host\r\n'
        res += f'process_name=main\r\n'
        res += f'intra_role=master\r\n'
        res += f'intra_host=localhost\r\n'
        res += f'intra_port=0\r\n'
        res += f'inter_port={port}\r\n'
        res += f'extra-index-url={extra_index_url}\r\n'
        res += f'package_dir=packages\r\n'
        res += 'starter=app_starter.py\r\n'
        with open(f'{SERVICE_SOURCE}/{CONFIG_NAME}', 'w') as f:
            f.write(res)

    async def install_pip(self, desc):
        system_name = desc.get(SYSTEM_NAME)
        conn = self.connections.get(system_name)
        if not conn:
            return False
        res = await conn.run('python3.10 -m ensurepip')
        if res.exit_status == 0:
            return True
        res = await conn.run('python3.10 -m pip --version')
        logging.debug(res)
        if res.exit_status == 0:
            return True
        res = await conn.run(f"sudo -S <<< '{desc[PASSWORD]}' apt install python3-pip -y")
        logging.debug(res)
        if res.exit_status != 0:
            return False
        return True

    async def create_venv(self, desc):
        system_name = desc.get(SYSTEM_NAME)
        conn = self.connections.get(system_name)
        if not conn:
            return False
        await conn.run(f'python3.10 -m venv {SERVICE_DESTINATION}/venv')
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
        # self.save_config()
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
