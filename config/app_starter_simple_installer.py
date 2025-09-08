
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
        query = self.adaptor.get_msg('get_credentials', {'credentials_name': 'ssh'}, self.adaptor.get_head_addr())
        ans = await self.adaptor.ask(query)
        body = ans.get('body') if isinstance(ans.get('body'), dict) else dict()
        username = body.get('username')
        password = body.get('password')
        class_desc = {'requires_dist': 'simple_installer', 'class': 'SimpleInstaller'}
        query = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'simple_installer'})
        ans = await self.adaptor.ask(query)
        body = {'system_name': 'local', 'host': '192.168.100.83', 'port': 6999, 'ssh_port': 22,
                'key_dir': '.ssh', 'key_name': 'id_rsa', 'username': username, 'password': password,
                'passphrase': 'qwerty', 'extra-index-url': f'http://{self.adaptor.get_param("ip")}:9000'}
        query = self.adaptor.get_msg('add_server', body, ans.get('body'))
        await self.adaptor.ask(query, 3000)
        raise KeyboardInterrupt()
