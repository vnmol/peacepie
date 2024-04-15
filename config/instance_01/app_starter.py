
class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        class_desc = {'package_name': 'simple_installer', 'class': 'SimpleInstaller'}
        query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'simple_installer'})
        ans = await self.adaptor.ask(query)
        body = {'system_name': 'local', 'host': '192.168.100.83', 'port': 6999, 'ssh_port': 22,
                'key_dir': '.ssh', 'key_name': 'id_rsa', 'username': 'admin', 'password': 'adminadmin',
                'passphrase': 'qwerty', 'extra-index-url': f'http://{self.adaptor.get_param("ip")}:9000'}
        query = self.adaptor.get_msg('add_server', body, ans.get('body'))
        await self.adaptor.ask(query, 1800)
        raise KeyboardInterrupt()
