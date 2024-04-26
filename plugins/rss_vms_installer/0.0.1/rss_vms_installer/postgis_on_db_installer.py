import logging
import psycopg2


class PostgisOnDbInstaller:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'postgis_on_db_install':
            await self.postgis_on_db_install(msg)
        else:
            return False
        return True

    async def postgis_on_db_install(self, msg):
        recipient = msg.get('sender')
        try:
            await self._postgis_on_db_install()
            await self.adaptor.send(self.adaptor.get_msg('postgis_on_db_is_installed', recipient=recipient))
        except Exception as e:
            logging.exception(e)
            await self.adaptor.send(self.adaptor.get_msg('postgis_on_db_is_not_installed', recipient=recipient))

    async def _postgis_on_db_install(self):
        user_name = 'vms'
        body = {'credentials_name': user_name}
        query = self.adaptor.get_msg('get_credentials', body, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        password = body.get('password')
        conn = psycopg2.connect(dbname='vms_ws', user='vms', password=password, host='localhost')
        cur = conn.cursor()
        cur.execute('CREATE EXTENSION postgis')
        cur.execute('CREATE EXTENSION postgis_topology')
        conn.commit()
        cur.close()
        conn.close()
