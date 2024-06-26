import logging
import re


UTF_VAL = 'URIEncoding="UTF-8"'
MAX_THREADS = 'maxThreads="40"'


def create_service_file(catalina_home):
    lines = '''
    [Unit]
    Description=Apache Tomcat Web Application Container
    After=network.target

    [Service]
    Type=forking

    Environment=JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/jre
    Environment=CATALINA_PID=<CATALINA_HOME>/temp/tomcat.pid
    Environment=CATALINA_HOME=<CATALINA_HOME>
    Environment=CATALINA_BASE=<CATALINA_HOME>
    Environment='JAVA_OPTS=-Djava.awt.headless=true -server -Xms2G -Xmx8G -XX:MaxMetaspaceSize=1G -XX:+UseConcMarkSweepGC -Dcommon.props.folder=<CATALINA_HOME>/lib/config/'

    ExecStart=<CATALINA_HOME>/bin/startup.sh
    ExecStop=<CATALINA_HOME>/bin/shutdown.sh

    User=tomcatuser
    Group=tomcatgroup

    [Install]
    WantedBy=multi-user.target
    '''
    lines = lines.replace('<CATALINA_HOME>', catalina_home)
    with open('/etc/systemd/system/tomcat_vms.service', 'w') as file:
        for line in lines.split('\n'):
            file.write(line.strip() + '\n')
    logging.debug('"/etc/systemd/system/tomcat_vms.service" is saved')


def replace(pair, param):
    lead = pair.group(1) + pair.group(2)
    return lead + param + lead + pair.group(3)


def attune(filename, port):
    with open(filename, 'r') as f:
        content = f.read()
    match = re.search(r'<Connector\s+port="\d+"\s+protocol="HTTP/1\.1"', content)
    if not match:
        logging.warning('Start of section is not found')
        return
    begin = match.start()
    end = content.find('/>', begin)
    if end == -1:
        logging.warning('End of section is not found')
        return
    section = content[begin:end]
    section = re.sub(r'(port=")\d+(")', lambda pair: pair.group(1) + str(port) + pair.group(2), section)
    if UTF_VAL not in section:
        section = re.sub(r'(\n)(\s+)(redirectPort=)', lambda pair: replace(pair, UTF_VAL), section)
    section = re.sub(r'(\n)(\s+)(redirectPort=)', lambda pair: replace(pair, MAX_THREADS), section)
    with open(filename, 'w') as f:
        f.write(content[:begin] + section + content[end:])


class Tomcat8523Installer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'tomcat_install':
            await self.tomcat_install(msg)
        else:
            return False
        return True

    async def tomcat_install(self, msg):
        recipient = msg.get('sender')
        try:
            await self._tomcat_install(msg)
            await self.adaptor.send(self.adaptor.get_msg('tomcat_is_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('tomcat_is_not_installed', recipient=recipient))

    async def _tomcat_install(self, msg):
        body = msg.get('body') if msg.get('body') else dict()
        await self.com_exe('groupadd tomcatgroup', 'Unable to create the "tomcatgroup"')
        com = 'adduser --home /home/tomcatuser --system --shell /bin/bash tomcatuser'
        await self.com_exe(com, 'Unable to create the "tomcatuser"')
        com = 'usermod -a -G tomcatgroup tomcatuser'
        await self.com_exe(com, 'Unable to add the "tomcatuser" to the "tomcatgroup"')
        com = 'wget https://archive.apache.org/dist/tomcat/tomcat-8/v8.5.23/bin/apache-tomcat-8.5.23.tar.gz'
        await self.com_exe(com, 'Unable to download the Tomcat distribution')
        com = 'tar -xf apache-tomcat-8.5.23.tar.gz'
        await self.com_exe(com, 'Unable to unzip the Tomcat distribution')
        com = 'mv apache-tomcat-8.5.23 /opt/tomcat-8.5.23_vms'
        await self.com_exe(com, 'Unable to move the Tomcat folder')
        await self.com_exe('rm apache-tomcat-8.5.23.tar.gz', 'Unable to remove the Tomcat distribution')
        com = 'chown -R tomcatuser:tomcatgroup /opt/tomcat-8.5.23_vms'
        await self.com_exe(com, 'Unable to change a folder owner')
        create_service_file(body.get('CATALINA_HOME'))
        await self.com_exe('systemctl daemon-reload', 'Error occurred while refresh services')
        await self.com_exe('systemctl start tomcat_vms.service', 'Unable to start Tomcat')
        await self.com_exe('systemctl enable tomcat_vms.service', 'Failed to enable Tomcat')
        port = int(body.get('tomcat_address').split(':')[-1])
        attune('/opt/tomcat-8.5.23_vms/conf/server.xml', port)
        await self.com_exe('systemctl stop tomcat_vms.service', 'Unable to stop Tomcat')

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
