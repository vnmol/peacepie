import logging


class LoggerInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'logger_install':
            await self.logger_install(msg)
        else:
            return False
        return True

    async def logger_install(self, msg):
        recipient = msg.get('sender')
        props = msg.get('body') if msg.get('body') else dict()
        try:
            await self._logger_install(props)
            await self.adaptor.send(self.adaptor.get_msg('logger_is_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('logger_is_not_installed', recipient=recipient))

    async def _logger_install(self, props):
        source = 'https://redmine.on-dev.ru/attachments/download/10108/logger_v1.6.19_lib_and_prop_files.zip'
        curl = {'command': 'curl', 'params': {'credentials_name': 'redmine', 'source': source}}
        unzip = {'command': 'unzip', 'params': {'destination': f'{props.get("CATALINA_HOME")}/lib'}}
        remove = {'command': 'remove', 'params': {}}
        body = {'actions': [curl, unzip, remove]}
        query = self.adaptor.get_msg('file_operations', body, props.get('auxiliary'))
        ans = await self.adaptor.ask(query, 300)
        if ans.get('command') != 'ready':
            body = ans.get('body') if ans.get('body') else dict()
            raise Exception(body.get('message'))
        source = 'https://redmine.on-dev.ru/attachments/download/10106/logger.war_v1.6.19.zip'
        curl = {'command': 'curl', 'params': {'credentials_name': 'redmine', 'source': source}}
        unzip = {'command': 'unzip', 'params': {'destination': f'{props.get("CATALINA_HOME")}/webapps'}}
        remove = {'command': 'remove', 'params': {}}
        body = {'actions': [curl, unzip, remove]}
        query = self.adaptor.get_msg('file_operations', body, props.get('auxiliary'))
        ans = await self.adaptor.ask(query, 300)
        if ans.get('command') != 'ready':
            body = ans.get('body') if ans.get('body') else dict()
            raise Exception(body.get('message'))
        com = f'chown -R tomcatuser:tomcatgroup {props.get("CATALINA_HOME")}'
        await self.adaptor.com_exe(com)
