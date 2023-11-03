import asyncio


class SimpleTcpClient:

    def __init__(self):
        self.adaptor = None
        self.inet_addr = None
        self.convertor_desc = None
        self.convertor = None
        self.balancer = None
        self.producer = None
        self.is_on_demand = True
        self.is_active = False
        self.writer = None

    async def handle(self, msg):
        if msg.command == 'raw_data':
            await self.raw_data(msg)
        elif msg.command == 'set_params':
            await self.set_params(msg.body['params'])
        elif msg.command == 'start':
            await self.start()
        else:
            return False
        return True

    async def raw_data(self, msg):
        if not self.is_active:
            asyncio.get_running_loop().create_task(self.handle_connection())
            await asyncio.sleep(0.1)
            if self.writer is None:
                await asyncio.sleep(1)
        if not self.writer:
            return
        self.writer.write(msg.body)
        await self.writer.drain()
        self.adaptor.logger.debug(self.adaptor.get_alias() + f' THE DATA FROM MESSAGE({msg.mid}) IS SENT')

    async def set_params(self, params):
        for param in params:
            if param['name'] == 'inet_addr':
                self.inet_addr = param['value']
            elif param['name'] == 'convertor_desc':
                self.convertor_desc = param['value']
            elif param['name'] == 'balancer':
                self.balancer = param['value']
            elif param['name'] == 'producer':
                self.producer = param['value']
            elif param['name'] == 'is_on_demand':
                self.is_on_demand = param['value']

    async def start(self):
        await self.create_convertor()
        if not self.is_on_demand:
            asyncio.get_running_loop().create_task(self.handle_connection())

    async def create_convertor(self):
        name = f'{self.adaptor.name}.convertor'
        msg = self.adaptor.get_msg('create_actor', {'class_desc': self.convertor_desc, 'name': name})
        msg.recipient = self.balancer
        answer = await self.adaptor.ask(msg)
        if answer.command != 'actor_is_created':
            return None
        self.adaptor.add_to_cache(answer.body['node'], answer.body['entity'])
        body = {'params':
                    [{'name': 'mediator', 'value': {'node': self.adaptor.get_node(), 'entity': self.adaptor.name}}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        body = {'params': [{'name': 'consumer', 'value': {'node': self.adaptor.get_node(), 'entity': name}}]}
        await self.adaptor.send(self.adaptor.get_msg('set_params', body, self.producer))
        await self.adaptor.send(self.adaptor.get_msg('start', recipient=self.producer))
        self.convertor = name

    async def handle_connection(self):
        self.is_active = True
        self.adaptor.logger.info(self.adaptor.get_alias() + ' Channel is active')
        reader = None
        while True:
            try:
                reader, self.writer = await asyncio.open_connection(self.inet_addr['host'], self.inet_addr['port'])
                self.adaptor.logger.info(self.adaptor.get_alias() + ' Channel is opened')
            except Exception as ex:
                self.adaptor.logger.exception(ex)
            while reader:
                if not self.adaptor.is_running or reader.at_eof():
                    break
                try:
                    data = await reader.read(255)
                except Exception as ex:
                    self.adaptor.logger.exception(ex)
                    reader = None
            if self.writer:
                self.adaptor.logger.info(self.adaptor.get_alias() + ' Channel is closed')
                self.writer.close()
                await self.writer.wait_closed()
            self.writer = None
            if self.is_on_demand:
                self.is_active = False
                self.adaptor.logger.info(self.adaptor.get_alias() + ' Channel is inactive')
                return
            else:
                await asyncio.sleep(10)
