class SimpleWebStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        # await self.adaptor.send(self.adaptor.get_msg('create_process'))
        # await self.adaptor.send(self.adaptor.get_msg('create_process'))
        class_desc = {"package_name": "simple_web_face", "class": "WebFace"}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'web_face_00'})
        await self.adaptor.ask(msg)
        await self.adaptor.send(self.adaptor.get_msg('start', {'port': 8080}, recipient='web_face_00'))
