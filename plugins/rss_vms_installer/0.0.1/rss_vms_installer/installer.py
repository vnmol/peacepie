import logging


class Stages:
    CURL = 0
    LOCALE = 1
    JAVA = 2
    POSTGRES = 3
    POSTGIS = 4
    TOMCAT = 5
    TOMCAT_TUNER = 6
    SERVER_PART = 7
    LOGGER = 8
    DATABASE = 9
    POSTGIS_ON_DB = 10
    POST_SCRIPTS = 11
    FINISH = 12
    POST_FINISH = 13


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
        class_desc = {'requires_dist': 'auxiliaries', 'class': 'Auxiliary'}
        query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'auxiliary'})
        ans = await self.adaptor.ask(query, 30)
        auxiliary = ans.get('body')
        body = msg.get('body')
        internal_starter = body.get('internal_starter')
        internal_starter = internal_starter if internal_starter else 'internal_starter'
        state = body.get('state')
        stage = state.get('stage')
        stage = stage if stage else Stages.CURL
        substage = state.get('substage')
        props = body.get('props')
        extended_props = props.copy()
        extended_props['auxiliary'] = auxiliary
        if stage == Stages.CURL:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'CurlInstaller'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'curl_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('curl_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 300)
            com = ans.get('command')
            if com != 'curl_is_installed':
                return
            stage = Stages.LOCALE
        if stage == Stages.LOCALE:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'Utf8RuLocaleInstaller'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'ru_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('ru_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 300)
            com = ans.get('command')
            if com == 'need_to_reboot':
                substage = ans.get('body').get('stage') if ans.get('stage') else None
                await self.reboot(internal_starter, stage, substage, props)
                return
            elif com != 'ru_is_installed':
                return
            stage = Stages.JAVA
        if stage == Stages.JAVA:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'OpenJdkJava8Installer'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'java_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('java_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 300)
            if ans.get('command') != 'java_is_installed':
                return
            stage = Stages.POSTGRES
        if stage == Stages.POSTGRES:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'Postgres11Installer'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'postgres_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('postgres_install', {'stage': substage}, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com == 'need_to_reboot':
                substage = ans.get('body').get('stage') if ans.get('body') else None
                await self.reboot(internal_starter, Stages.POSTGRES, substage, props)
                return
            elif com != 'postgres_is_installed':
                return
            stage = Stages.POSTGIS
        if stage == Stages.POSTGIS:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'PostGIS25Installer'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'postgis_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('postgis_install', recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'postgis_is_installed':
                return
            stage = Stages.TOMCAT
        if stage == Stages.TOMCAT:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'Tomcat8523Installer'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'tomcat_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('tomcat_install', extended_props, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'tomcat_is_installed':
                return
            stage = Stages.TOMCAT_TUNER
        if stage == Stages.TOMCAT_TUNER:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'TomcatTuner'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'tomcat_tuner'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('tomcat_tune', extended_props, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'tomcat_is_tuned':
                return
            stage = Stages.SERVER_PART
        if stage == Stages.SERVER_PART:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'ServerPartInstaller'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'server_part_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('server_part_install', extended_props, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'server_part_is_installed':
                return
            stage = Stages.LOGGER
        if stage == Stages.LOGGER:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'LoggerInstaller'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'logger_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('logger_install', extended_props, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'logger_is_installed':
                return
            stage = Stages.DATABASE
        if stage == Stages.DATABASE:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'DatabaseCreator'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'database_creator'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('create_database', None, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'database_is_created':
                return
            stage = Stages.POSTGIS_ON_DB
        if stage == Stages.POSTGIS_ON_DB:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'PostgisOnDbInstaller'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'postgis_on_db_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('postgis_on_db_install', None, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'postgis_on_db_is_installed':
                return
            stage = Stages.POST_SCRIPTS
        if stage == Stages.POST_SCRIPTS:
            class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'PostScriptsInstaller'}
            query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'post_scripts_installer'})
            ans = await self.adaptor.ask(query, 30)
            query = self.adaptor.get_msg('post_scripts_install', extended_props, recipient=ans.get('body'))
            ans = await self.adaptor.ask(query, 1200)
            com = ans.get('command')
            if com != 'post_scripts_are_installed':
                return
            stage = Stages.POST_FINISH
        if stage == Stages.FINISH or stage == Stages.POST_FINISH:
            body = {'name': self.adaptor.name, 'txt': get_txt(stage, substage, props)}
            await self.adaptor.ask(self.adaptor.get_msg('app_starter', body, internal_starter))

    async def reboot(self, internal_starter, stage, substage, props):
        body = {'name': self.adaptor.name, 'txt': get_txt(stage, substage, props)}
        await self.adaptor.ask(self.adaptor.get_msg('app_starter', body, internal_starter))
        com = 'reboot now'
        res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=([com], 300))
        logging.debug(f'{com}: {res}')


def get_txt(stage, substage, props):
    if stage == Stages.FINISH:
        return 'pass\n'
    state = {'stage': stage, 'substage': substage}
    res = '''
    internal_starter = None
    body = msg.get('body')
    if body:
        internal_starter = body.get('internal_starter')
    if not internal_starter:
        internal_starter = 'internal_starter'
    class_desc = {'requires_dist': 'rss_vms_installer', 'class': 'RssVmsInstaller'}
    body = {'class_desc': class_desc, 'name': 'vms_installer'}
    query = self.adaptor.get_msg('create_actor', body)
    ans = await self.adaptor.ask(query, 30)
    body = {'internal_starter': internal_starter, '''
    res += f"'state': {state}, 'props': {props}" + "}"
    res += '''
    await self.adaptor.send(self.adaptor.get_msg('start', body, recipient=ans.get('body')))
    '''
    return res
