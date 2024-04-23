import logging
import os
import zipfile


class Auxiliary:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'file_operations':
            await self.file_operations(msg)
        else:
            return False
        return True

    async def file_operations(self, msg):
        recipient = msg.get('sender')
        try:
            await self._file_operations(msg)
            await self.adaptor.send(self.adaptor.get_msg('ready', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('not_ready', {'message': str(e)}, recipient))

    async def _file_operations(self, msg):
        body = msg.get('body') if msg.get('body') else dict()
        actions = body.get('actions') if body.get('actions') else []
        res = None
        for action in actions:
            command = action.get('command')
            params = action.get('params')
            if not params.get('source'):
                params['source'] = res
            if command == 'curl':
                res = await self.curl(params)
            elif command == 'unzip':
                res = await self.unzip(params)
            elif command == 'remove':
                res = await self.remove(params)
            else:
                raise Exception(f'Unknown_command "{command}"')

    async def curl(self, params):
        source = params.get('source')
        credentials_name = params.get('credentials_name')
        credentials = ''
        if credentials_name:
            body = {'credentials_name': credentials_name}
            query = self.adaptor.get_msg('get_credentials', body, self.adaptor.get_head_addr())
            ans = await self.adaptor.ask(query)
            body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
            credentials = f'-u {body.get("username")}:{body.get("password")} '
        await self.adaptor.com_exe(f'curl {credentials}-O {source}')
        return os.path.basename(source)

    async def unzip(self, params):
        source = params.get('source')
        destination = params.get('destination')
        with zipfile.ZipFile(source, 'r') as zip_ref:
            zip_ref.extractall(destination)
        logging.debug(f'"{source}" is successfully unzipped to "{destination}"')
        return source

    async def remove(self, params):
        source = params.get('source')
        os.remove(source)
        logging.debug(f'"{source}" is successfully removed')
