import logging


class PostGIS25Installer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'postgis_install':
            await self.postgis_install(msg)
        else:
            return False
        return True

    async def postgis_install(self, msg):
        recipient = msg.get('sender')
        try:
            com = 'apt install postgis postgresql-11-postgis-2.5 -y'
            res = await self.adaptor.sync_as_async(self.adaptor.execute, sync_args=([com], 300))
            if res[0] == 0:
                await self.adaptor.send(self.adaptor.get_msg('postgis_is_installed', recipient=recipient))
                return
        except Exception as e:
            logging.exception(e)
        await self.adaptor.send(self.adaptor.get_msg('postgis_is_not_installed', recipient=recipient))

