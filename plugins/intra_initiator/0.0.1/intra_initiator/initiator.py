

class KingInitiator:

    def __init__(self):
        self.adaptor = None
        self.version = {'==': {'major': 0, 'minor': 0, 'micro': 1}}
        self.class_desc = {'package_name': 'intra_initiator', 'version': self.version, 'class': 'IntraTester'}
        self.kafka_uploader = None
        self.first = None
        self.last = None
        self.indx = 0

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            await self.start()
        elif command == 'notification':
            await self.notification(msg['body'])
        else:
            return False
        return True

    async def start(self):
        class_desc = {'package_name': 'simple_kafka_uploader', 'version': self.version, 'class': 'SimpleKafkaUploader'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'kafka_uploader'})
        ans = await self.adaptor.ask(msg, 5)
        self.kafka_uploader = ans['body']
        body = {'params': [{'name': 'bootstrap_servers', 'value': 'localhost'},
                           {'name': 'topic_name', 'value': 'nddata'}]}
        msg = self.adaptor.get_msg('set_params', body, self.kafka_uploader)
        await self.adaptor.ask(msg)
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=self.kafka_uploader))
        head = self.adaptor.get_head_addr()
        self_addr = self.adaptor.get_self_addr()
        body = {'system': {'name': 'queen', 'addr': {'host': '192.168.100.163', 'port': 6001}}}
        msg = self.adaptor.get_msg('inter_register_system', body, head)
        await self.adaptor.send(msg)
        msg = self.adaptor.get_msg('subscribe', {'command': 'inter_linked'}, head, self_addr)
        await self.adaptor.send(msg)
        msg = self.adaptor.get_msg('inter_connect', {'system_name': 'queen'}, head)
        await self.adaptor.send(msg)
        # msg = self.adaptor.get_msg('subscribe', {'command': 'intra_linked'}, head, self_addr)
        # await self.adaptor.send(msg)
        name = f'tester_{self.indx:02d}'
        msg = self.adaptor.get_msg('create_actor', {'class_desc': self.class_desc, 'name': name})
        ans = await self.adaptor.ask(msg, 5)
        self.first = ans['body']
        # await self.create_generator(self.adaptor.get_node())

    async def notification(self, original):
        command = original['command']
        if command == 'inta_linked':
            pass
            # await self.notif_intra_linked(original)
        elif command == 'inter_linked':
            await self.notif_inter_linked(original)

    async def notif_intra_linked(self, original):
        node = original['body']['name']
        self.indx += 1
        name = f'tester_{self.indx:02d}'
        addr = self.adaptor.get_addr(None, node, None)
        msg = self.adaptor.get_msg('create_actor', {'class_desc': self.class_desc, 'name': name}, addr)
        await self.adaptor.ask(msg)
        msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'consumer', 'value': self.first}]}, name)
        await self.adaptor.ask(msg)
        last = self.last if self.last else self.first
        msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'consumer', 'value': name}]}, last)
        await self.adaptor.ask(msg)
        if not self.last:
            await self.adaptor.send(self.adaptor.get_msg('start', recipient=self.first))
        self.last = name
        if not original['body']['lord']:
            await self.create_generator(node)

    async def notif_inter_linked(self, original):
        system_name = original['body']['system_name']
        system_addr = self.adaptor.get_addr(system_name, None, None)
        self.indx += 1
        body = {'class_desc': self.class_desc, 'name': f'tester_{self.indx:02d}'}
        msg = self.adaptor.get_msg('create_actor', body, system_addr)
        ans = await self.adaptor.ask(msg)
        last = ans['body']
        body = {'params': [{'name': 'consumer', 'value': last}, {'name': 'kafka_uploader', 'value': self.kafka_uploader}]}
        msg = self.adaptor.get_msg('set_params', body, self.first)
        await self.adaptor.ask(msg)
        for i in range(3):
            ans = await self.adaptor.ask(self.adaptor.get_msg('create_process', recipient=system_addr))
            self.indx += 1
            body = {'class_desc': self.class_desc, 'name': f'tester_{self.indx:02d}'}
            msg = self.adaptor.get_msg('create_actor', body, ans['body'])
            ans = await self.adaptor.ask(msg, 5)
            cur = ans['body']
            msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'consumer', 'value': cur}]}, last)
            await self.adaptor.ask(msg)
            last = cur
        msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'consumer', 'value': self.first}]}, last)
        await self.adaptor.ask(msg)
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=self.first))

    async def create_actor(self, system_name, name, consumer, addr):
        msg = self.adaptor.get_msg('create_actor', {'class_desc': self.class_desc, 'name': name}, addr)
        await self.adaptor.ask(msg)
        name = self.adaptor.get_addr(system_name, None, name)
        msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'consumer', 'value': consumer}]}, name)
        await self.adaptor.ask(msg)

    async def create_generator(self, node):
        class_desc = {'package_name': 'intra_initiator', 'version': self.version, 'class': 'ProcessGen'}
        name = f'{node[:node.find(".")]}_gen'
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': name})
        await self.adaptor.ask(msg)
        recipient = self.adaptor.get_addr(None, node, None)
        msg = self.adaptor.get_msg('set_params', {'params': [{'name': 'recipient', 'value': recipient}]}, name)
        await self.adaptor.send(msg)
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=name))


class QueenInitiator:

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
        head = self.adaptor.get_head_addr()
        body = {'system': {'name': 'king', 'addr': {'host': '192.168.100.163', 'port': 6000}}}
        msg = self.adaptor.get_msg('inter_register_system', body, head)
        await self.adaptor.send(msg)


class ProcessGen:

    def __init__(self):
        self.adaptor = None
        self.recipient = None
        self.period = 10
        self.count = 4

    async def handle(self, msg):
        command = msg['command']
        if command == 'start':
            self.adaptor.add_ticker(self.period, self.count)
        elif command == 'set_params':
            self.set_params(msg['body']['params'])
        elif command == 'tick':
            await self.adaptor.send(self.adaptor.get_msg('create_process', recipient=self.recipient))
        else:
            return False
        return True

    def set_params(self, params):
        for param in params:
            if param['name'] == 'recipient':
                self.recipient = param['value']
