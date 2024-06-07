
class Initiator:

    def __init__(self):
        self.adaptor = None
        self.is_loop = None
        self.tester_name = 'tester'
        self.group_count = None
        self.group_size = None
        self.with_dests = None
        self.dest_type = None
        self.dest_name = 'dest'
        self.with_gens = None
        self.gen_type = None
        self.gen_name = 'gen'
        self.period = None
        self.direct = None
        self.detail_log = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'start':
            await self.start()
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        else:
            return False
        return True

    async def start(self):
        if self.is_loop:
            for index in range(self.group_count):
                await self.adaptor.send(self.adaptor.get_msg('test', None, f'{self.tester_name}_{index:02d}_00'))
        else:
            for name in self.get_gen_names():
                await self.adaptor.send(self.adaptor.get_msg('start', None, name))

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'is_loop':
                self.is_loop = value
            elif name == 'group_count':
                self.group_count = value
            elif name == 'group_size':
                self.group_size = value
            elif name == 'with_dests':
                self.with_dests = value
            elif name == 'dest_type':
                self.dest_type = value
            elif name == 'with_gens':
                self.with_gens = value
            elif name == 'gen_type':
                self.gen_type = value
            elif name == 'period':
                self.period = value
            elif name == 'direct':
                self.direct = value
            elif name == 'detail_log':
                self.detail_log = value
        await self.prepare()
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def prepare(self):
        await self.create_actors()
        await self.create_links()

    async def create_actors(self):
        await self.create_dests()
        await self.create_gens()
        await self.create_testers()

    async def create_dests(self):
        names = []
        if self.dest_type == 'for_each':
            names = [f'{self.dest_name}_{m:02d}_{n:02d}'
                     for n in range(self.group_size) for m in range(self.group_count)]
        elif self.dest_type == 'for_group':
            names = [f'{self.dest_name}_{m:02d}' for m in range(self.group_count)]
        elif self.dest_type == 'for_all':
            names = [self.dest_name]
        body = {'class_desc': {'package_name': 'simple_tester', 'class': 'SimpleDest'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)

    async def create_gens(self):
        body = {'class_desc': {'package_name': 'simple_tester', 'class': 'SimpleGen'}, 'names': self.get_gen_names()}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)

    def get_gen_names(self):
        res = []
        if self.gen_type == 'for_each':
            res = [f'{self.gen_name}_{m:02d}_{n:02d}' for m in range(self.group_count) for n in range(self.group_size)]
        elif self.gen_type == 'for_group':
            res = [f'{self.gen_name}_{m:02d}' for m in range(self.group_count)]
        elif self.gen_type == 'for_all':
            res = [self.gen_name]
        return res

    async def create_testers(self):
        names = [f'{self.tester_name}_{m:02d}_{n:02d}' for m in range(self.group_count) for n in range(self.group_size)]
        body = {'class_desc': {'package_name': 'simple_tester', 'class': 'SimpleTester'}, 'names': names}
        await self.adaptor.ask(self.adaptor.get_msg('create_actors', body), 4)

    def get_length(self, kind):
        res = 0
        if kind == 'for_each':
            res = self.group_count * self.group_size
        elif kind == 'for_group':
            res = self.group_count
        elif kind == 'for_all':
            res = 1
        return res

    async def create_links(self):
        await self.gen_links()
        await self.tester_links()

    async def gen_links(self):
        length = self.get_length(self.gen_type)
        if length == 0:
            return
        await self.adaptor.group_ask(10, length, self.gen_factory())

    def gen_factory(self):

        def get_values(index):
            body = {'params': [{'name': 'consumers', 'value': self.get_gen_consumers(index)},
                               {'name': 'period', 'value': self.period},
                               {'name': 'detail_log', 'value': self.detail_log}]}
            return {'command': 'set_params', 'body': body, 'recipient': self.get_gen_name(index)}

        return get_values

    def get_gen_name(self, index):
        res = None
        if self.gen_type == 'for_each':
            res = f'{self.gen_name}_{index // self.group_size:02d}_{index % self.group_size:02d}'
        elif self.gen_type == 'for_group':
            res = f'{self.gen_name}_{index:02d}'
        elif self.gen_type == 'for_all':
            res = self.gen_name
        return res

    def get_gen_consumers(self, index):
        res = []
        if self.direct:
            if self.gen_type == 'for_each':
                res = [f'{self.dest_name}_{index // self.group_size:02d}_{index % self.group_size:02d}']
            elif self.gen_type == 'for_group':
                res = [f'{self.dest_name}_{index:02d}_{n:02d}' for n in range(self.group_size)]
            elif self.gen_type == 'for_all':
                res = [f'{self.dest_name}_{m:02d}_{n:02d}'
                       for m in range(self.group_count) for n in range(self.group_size)]
        elif self.with_gens:
            if self.gen_type == 'for_each':
                res = [f'{self.tester_name}_{index // self.group_size:02d}_{index % self.group_size:02d}']
            elif self.gen_type == 'for_group':
                res = [f'{self.tester_name}_{index:02d}_{n:02d}' for n in range(self.group_size)]
            elif self.gen_type == 'for_all':
                res = [f'{self.tester_name}_{m:02d}_{n:02d}'
                       for m in range(self.group_count) for n in range(self.group_size)]
        return res

    async def tester_links(self):
        if not (self.is_loop or self.with_dests):
            return
        await self.adaptor.group_ask(10, self.group_count * self.group_size, self.tester_factory())

    def tester_factory(self):

        def get_values(index):
            body = {'params': [{'name': 'next', 'value': self.get_tester_next(index)},
                               {'name': 'consumer', 'value': self.get_tester_consumer(index)},
                               {'name': 'detail_log', 'value': self.detail_log}]}
            return {'command': 'set_params', 'body': body, 'recipient': self.get_tester_name(index)}

        return get_values

    def get_tester_name(self, index):
        return f'{self.tester_name}_{index // self.group_size:02d}_{index % self.group_size:02d}'

    def get_tester_next(self, index):
        if not self.is_loop:
            return None
        return f'{self.tester_name}_{index // self.group_size:02d}_{(index + 1) % self.group_size:02d}'

    def get_tester_consumer(self, index):
        res = None
        if not self.with_dests:
            return res
        if self.dest_type == 'for_each':
            res = f'{self.dest_name}_{index // self.group_size:02d}_{index % self.group_size:02d}'
        elif self.dest_type == 'for_group':
            res = f'{self.dest_name}_{index // self.group_size:02d}'
        elif self.dest_type == 'for_all':
            res = self.dest_name
        return res
