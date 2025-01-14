
class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.web_face()
        await self.django()

    async def web_face(self):
        name = 'web_face'
        body = {'class_desc': {'package_name': 'simple_web_face', 'class': 'SimpleWebFace'}, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('start', {'port': 9090}, name), 10)

    async def django(self):
        name = 'docker_installer'
        class_desc = {'package_name': 'simple_docker_manager', 'class': 'SimpleDockerInstaller'}
        body = {'class_desc': class_desc, 'name': name}
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        await self.adaptor.ask(self.adaptor.get_msg('install', None, name), 300)
