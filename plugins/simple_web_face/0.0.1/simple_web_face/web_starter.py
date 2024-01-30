class SimpleWebStarter:

    def __init__(self):
        self.adaptor = None
        self.index = 0

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start()
        elif command == 'notification':
            await self.notification(msg)
        else:
            return False
        return True

    async def start(self):
        await self.create_actors(None)
        head = self.adaptor.get_head_addr()
        self_addr = self.adaptor.get_self_addr()
        msg = self.adaptor.get_msg('subscribe', {'command': 'intra_linked'}, head, self_addr)
        await self.adaptor.send(msg)
        for _ in range(4):
            await self.adaptor.send(self.adaptor.get_msg('create_process'))
        class_desc = {'package_name': 'simple_web_face', 'class': 'WebFace'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'web_face_00'})
        await self.adaptor.ask(msg, 5)
        await self.adaptor.send(self.adaptor.get_msg('start', {'port': 8080}, recipient='web_face_00'))

    async def notification(self, msg):
        body = msg.get('body').get('body')
        node = body.get('name')
        recipient = {'node': node, 'entity': None}
        await self.create_actors(recipient)
        if body.get('lord'):
            return
        for _ in range(4):
            await self.adaptor.send(self.adaptor.get_msg('create_process', recipient=recipient))

    async def create_actors(self, recipient):
        class_desc = {'package_name': 'simple_web_face', 'class': 'Stub'}
        names = [f'stub_{self.index:02d}_{n:02d}' for n in range(30)]
        self.index += 1
        msg = self.adaptor.get_msg('create_actors', {'class_desc': class_desc, 'names': names}, recipient=recipient)
        await self.adaptor.send(msg)
