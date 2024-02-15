class RssInstaller:
    
    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'vms_install':
            await self.vms_install(msg)
        else:
            return False
        return True
    
    async def vms_install(self, msg):
        class_desc = {'package_name': 'simple_ssh_connector', 'class': 'SimpleSshConnector'}
        query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'connector'})
        ans = await self.adaptor.ask(query, 20)
        ans = await self.adaptor.ask(self.adaptor.get_msg('ssh_connect', msg.get('body'), ans.get('body')), 8)
        if ans.get('command') != 'ssh_connected':
            return
        body = {'addr': {'host': self.adaptor.get_param('ip'), 'port': ans.get('body').get('port')}}
        ans = await self.adaptor.ask(self.adaptor.get_msg('inter_connect', body, self.adaptor.get_head_addr()))
        query = self.adaptor.get_msg('create_process', None, ans.get('body'))
        ans = await self.adaptor.ask(query)
        class_desc = {'package_name': 'rss_vms_installer', 'class': 'RssVmsInstaller'}
        body = {'class_desc': class_desc, 'name': 'installer'}
        query = self.adaptor.get_msg('create_actor', body, ans.get('body'))
        await self.adaptor.ask(query, 20)
        query['recipient'] = None
        await self.adaptor.ask(query, 20)
