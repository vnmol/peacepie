import logging
import os
import shutil


class PostScriptsInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'post_scripts_install':
            await self.post_scripts_install(msg)
        else:
            return False
        return True

    async def post_scripts_install(self, msg):
        recipient = msg.get('sender')
        props = msg.get('body') if msg.get('body') else dict()
        try:
            await self._post_scripts_install(props)
            await self.adaptor.send(self.adaptor.get_msg('post_scripts_are_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('post_scripts_are_not_installed', recipient=recipient))

    async def _post_scripts_install(self,props):
        dest = str(os.getcwd())
        source = 'https://redmine.on-dev.ru/attachments/download/10088/post_scripts_birt_to_vms.zip'
        curl = {'command': 'curl', 'params': {'credentials_name': 'redmine', 'source': source}}
        unzip = {'command': 'unzip', 'params': {'destination': dest}}
        remove = {'command': 'remove', 'params': {}}
        body = {'actions': [curl, unzip, remove]}
        query = self.adaptor.get_msg('file_operations', body, props.get('auxiliary'))
        ans = await self.adaptor.ask(query, 300)
        if ans.get('command') != 'ready':
            body = ans.get('body') if ans.get('body') else dict()
            raise Exception(body.get('message'))
        user_name = 'vms'
        body = {'credentials_name': user_name}
        query = self.adaptor.get_msg('get_credentials', body, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        password = body.get('password')
        filename = 'post_scripts.sh'
        with open(filename, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('su - root << EOF\n')
            f.write(f'cd {dest}/post_scripts_birt_to_vms\n')
            f.write(f'echo "{password}" | psql -h localhost -U {user_name} -d vms_ws -f ___all_files.sql\n')
            f.write('EOF\n')
        await self.adaptor.com_exe(f'chmod +x {filename}')
        await self.adaptor.com_exe(f'./{filename}')
        await self.adaptor.com_exe(f'rm {filename}')
        path = f'{dest}/post_scripts_birt_to_vms'
        if os.path.exists(path):
            shutil.rmtree(path)
        await self.adaptor.com_exe('systemctl start tomcat_vms.service')
