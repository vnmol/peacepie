import logging
import os
import zipfile


def move(src, dst):
    for filename in os.listdir(src):
        os.rename(f'{src}/{filename}', f'{dst}/{filename}')


class TomcatTuner:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'tomcat_tune':
            await self.tomcat_tune(msg)
        else:
            return False
        return True

    async def tomcat_tune(self, msg):
        recipient = msg.get('sender')
        try:
            await self._tomcat_tune(msg)
            await self.adaptor.send(self.adaptor.get_msg('tomcat_is_tuned', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('tomcat_is_not_tuned', recipient=recipient))

    async def _tomcat_tune(self, msg):
        query = self.adaptor.get_msg('get_credentials', {'credentials_name': 'redmine'}, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        credentials = f'{body.get("username")}:{body.get("password")}'
        body = msg.get('body') if msg.get('body') else dict()
        catalina_home = body.get('CATALINA_HOME')
        com = f'curl -u {credentials} -O https://redmine.on-dev.ru/attachments/download/10018/add_lib.zip'
        await self.com_exe(com, 'Unable to download the Tomcat addins')
        await self.com_exe('unzip add_lib.zip', 'Unable to unzip the Tomcat addins')
        await self.com_exe('rm add_lib.zip', 'Unable to remove "add_lib" archive')
        await self.com_exe('rm ./add_lib/postgresql-42.2.5.jar', 'Unable to delete postgres driver')
        com = 'wget -P ./add_lib https://jdbc.postgresql.org/download/postgresql-42.7.3.jar'
        await self.com_exe(com, 'Unable to download postgres driver')
        move('./add_lib', f'{catalina_home}/lib')
        await self.com_exe('rmdir add_lib', 'Unable to remove "add_lib" folder')
        com = f'curl -u {credentials} -O https://redmine.on-dev.ru/attachments/download/3380/arial.ttf.zip'
        await self.com_exe(com, 'Unable to download arial font archive')
        with zipfile.ZipFile('arial.ttf.zip', 'r') as zip_ref:
            zip_ref.extractall('/usr/share/fonts/truetype')
        await self.com_exe('rm arial.ttf.zip', 'Unable to remove arial font archive')
        self.tomcat_to_bd_tune(catalina_home)

    def tomcat_to_bd_tune(self, catalina_home):
        path = f'{catalina_home}/conf/context.xml'
        content = ''.join([
            '<Resource\n'
            'name="jdbc/vmsDS"\n',
            'auth="Container"\n',
            'type="javax.sql.DataSource"\n',
            'driverClassName="org.postgresql.Driver"\n',
            'factory="org.apache.tomcat.jdbc.pool.DataSourceFactory"\n',
            'url="jdbc:postgresql://localhost:5432/vms_ws"\n',
            'username="vms"\n',
            'password="vms"\n',
            'maxWaitMillis="-1"\n',
            '/>\n',
        ])
        with open(path, 'r') as f:
            data = f.read()
        if "</Context>" in data:
            index = data.rindex("</Context>")
            data = data[:index] + content + data[index:]
        else:
            data += content
        with open(path, 'w') as file:
            file.write(data)
            
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
