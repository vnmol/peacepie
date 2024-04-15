import logging


class Stages:
    LOCALE = 0
    JAVA = 1
    POSTGRES = 2
    POSTGIS = 3
    TOMCAT = 4
    FINISH = 5


class RssVmsInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        internal_starter = None
        stage = None
        substage = None
        body = msg.get('body')
        if body:
            internal_starter = body.get('internal_starter')
            stage = body.get('stage')
            substage = body.get('substage')
        internal_starter = internal_starter if internal_starter else 'internal_starter'
        stage = stage if stage else Stages.LOCALE
        if stage == Stages.LOCALE:
            class_desc = {'package_name': 'rss_vms_installer', 'class': 'Utf8RuLocaleInstaller'}
            msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'ru_installer'})
            ans = await self.adaptor.ask(msg, 30)
            msg = self.adaptor.get_msg('ru_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(msg, 300)
            com = ans.get('command')
            if com == 'need_to_reboot':
                substage = ans.get('body').get('stage') if ans.get('stage') else None
                await self.reboot(internal_starter, Stages.POSTGRES, substage)
                return
            elif com != 'ru_is_installed':
                return
            stage = Stages.JAVA
        if stage == Stages.JAVA:
            class_desc = {'package_name': 'rss_vms_installer', 'class': 'OpenJdkJava8Installer'}
            msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'java_installer'})
            ans = await self.adaptor.ask(msg, 30)
            msg = self.adaptor.get_msg('java_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(msg, 300)
            if ans.get('command') != 'java_is_installed':
                return
            stage = Stages.POSTGRES
        if stage == Stages.POSTGRES:
            class_desc = {'package_name': 'rss_vms_installer', 'class': 'Postgres11Installer'}
            msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'postgres_installer'})
            ans = await self.adaptor.ask(msg, 30)
            msg = self.adaptor.get_msg('postgres_install', {'stage': substage}, recipient=ans.get('body'))
            ans = await self.adaptor.ask(msg, 1200)
            com = ans.get('command')
            if com == 'need_to_reboot':
                substage = ans.get('body').get('stage') if ans.get('body') else None
                await self.reboot(internal_starter, Stages.POSTGRES, substage)
                return
            elif com != 'postgres_is_installed':
                return
            stage = Stages.POSTGIS
        if stage == Stages.POSTGIS:
            class_desc = {'package_name': 'rss_vms_installer', 'class': 'PostGIS25Installer'}
            msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'postgis_installer'})
            ans = await self.adaptor.ask(msg, 30)
            msg = self.adaptor.get_msg('postgis_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(msg, 1200)
            com = ans.get('command')
            if com != 'postgis_is_installed':
                return
            stage = Stages.TOMCAT
        if stage == Stages.TOMCAT:
            class_desc = {'package_name': 'rss_vms_installer', 'class': 'Tomcat8523Installer'}
            msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'tomcat_installer'})
            ans = await self.adaptor.ask(msg, 30)
            msg = self.adaptor.get_msg('tomcat_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(msg, 1200)
            com = ans.get('command')
            if com != 'tomcat_is_installed':
                return
            stage = Stages.FINISH
        if stage == Stages.FINISH:
            body = {'name': self.adaptor.name, 'txt': get_txt(stage, substage)}
            await self.adaptor.ask(self.adaptor.get_msg('app_starter', body, internal_starter))

    async def reboot(self, internal_starter, stage, substage):
        body = {'name': self.adaptor.name, 'txt': get_txt(stage, substage)}
        await self.adaptor.ask(self.adaptor.get_msg('app_starter', body, internal_starter))
        com = 'reboot now'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=([com], 300))
        logging.debug(f'{com}: {res}')


def get_txt(stage, substage):
    if stage == Stages.FINISH:
        return 'pass\n'
    res = '''
    internal_starter = None
    body = msg.get('body')
    if body:
        internal_starter = body.get('internal_starter')
    if not internal_starter:
        internal_starter = 'internal_starter'
    class_desc = {'package_name': 'rss_vms_installer', 'class': 'RssVmsInstaller'}
    body = {'class_desc': class_desc, 'name': 'vms_installer'}
    query = self.adaptor.get_msg('create_actor', body)
    ans = await self.adaptor.ask(query, 30)
    body = {'internal_starter': internal_starter, '''
    res += f"'stage': {stage}, 'substage': {substage}" + "}"
    res += '''
    await self.adaptor.send(self.adaptor.get_msg('start', body, recipient=ans.get('body')))
    '''
    return res
