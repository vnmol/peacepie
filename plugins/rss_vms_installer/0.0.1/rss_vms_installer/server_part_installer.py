import logging
import zipfile


class ServerPartInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'server_part_install':
            await self.server_part_install(msg)
        else:
            return False
        return True

    async def server_part_install(self, msg):
        recipient = msg.get('sender')
        try:
            await self._server_part_install(msg)
            await self.adaptor.send(self.adaptor.get_msg('server_part_is_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('server_part_is_not_installed', recipient=recipient))

    async def _server_part_install(self, msg):
        query = self.adaptor.get_msg('get_credentials', {'credentials_name': 'redmine'}, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        credentials = f'{body.get("username")}:{body.get("password")}'
        body = msg.get('body') if msg.get('body') else dict()
        catalina_home = body.get('CATALINA_HOME')
        await self.config_load(credentials, f'{catalina_home}/lib/config')
        await self.config_edit(body)
        com = f'curl -u {credentials} -O https://redmine.on-dev.ru/attachments/download/9499/vms-ws.war'
        await self.com_exe(com, 'Unable to load vms-ws.war')
        com = f'mv vms-ws.war {catalina_home}/webapps'
        await self.com_exe(com, 'Unable to move "vms-ws.war" to "webapps" folder')

    async def config_load(self, credentials, config_path):
        self.adaptor.makedir(config_path, True)
        logging.debug(f'{config_path} is created')
        com = f'curl -u {credentials} -O https://redmine.on-dev.ru/attachments/download/10111/vms-ws.prop.zip'
        await self.com_exe(com, 'Unable to load vms-ws.prop.zip')
        with zipfile.ZipFile('vms-ws.prop.zip', 'r') as zip_ref:
            zip_ref.extractall(config_path)
        logging.debug(f'vms-ws.prop is unzipped to {config_path}')
        await self.com_exe('rm vms-ws.prop.zip', 'Unable to remove vms-ws.prop.zip')
        com = f'curl -u {credentials} -O https://redmine.on-dev.ru/attachments/download/3547/system.messages.zip'
        await self.com_exe(com, 'Unable to load system.messages.zip')
        with zipfile.ZipFile('system.messages.zip', 'r') as zip_ref:
            zip_ref.extractall(config_path)
        logging.debug(f'system.messages is unzipped to {config_path}')
        await self.com_exe('rm system.messages.zip', 'Unable to remove system.messages.zip')

    async def config_edit(self, body):
        config_path = f'{body.get("CATALINA_HOME")}/lib/config/vms-ws.prop'
        tomcat_address = (f'vms-ws.soap.services.url={body.get("tomcat_address")}/vms-ws/services/\n'
                          .replace(':', '\\:'))
        upload_path = body.get('upload_path')
        with open(config_path, 'r') as file:
            lines = file.readlines()
        is_upload_path_exists = False
        for i, line in enumerate(lines):
            if line.startswith('vms-ws.soap.services.url='):
                lines[i] = tomcat_address
            if line.startswith('upload.path='):
                lines[i] = f'upload.path={upload_path}'
                is_upload_path_exists = True
        if not is_upload_path_exists:
            lines.append(f'upload.path={upload_path}')
        self.adaptor.makedir(upload_path)
        com = f'chown -R tomcatuser:tomcatgroup {upload_path}'
        await self.com_exe(com, f'Unable to change an owner for folder "{upload_path}"')
        with open(config_path, 'w') as file:
            file.writelines(lines)

    async def com_exe(self, coms, error, timeout=300):
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
        if res[0] != 0:
            raise Exception(error)
