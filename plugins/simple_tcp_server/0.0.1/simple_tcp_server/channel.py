from simple_tcp_server import mediator, tcp_server


class Channel:

    def __init__(self, parent, reader, writer):
        self.parent = parent
        self.id = next(tcp_server.gen_id)
        self.name = f'channel_{self.id}'
        self.reader = reader
        self.writer = writer
        self.mediator = None
        self.convertor = None

    async def handle(self):
        self.mediator = await self.create_mediator()
        self.convertor = await self.create_convertor()
        self.parent.adaptor.logger.info(f'{self.parent.adaptor.get_alias(self)} Channel is opened')
        while True:
            if not self.parent.adaptor.is_running or self.reader.at_eof():
                break
            try:
                data = await self.reader.read(255)
                self.parent.adaptor.logger.debug(f'{self.parent.adaptor.get_alias(self)} THE DATA IS RECEIVED')
                await self.parent.adaptor.send(self.parent.adaptor.get_msg('raw_data', data, self.convertor), self)
            except Exception as ex:
                self.parent.adaptor.logger.exception(ex)
        self.writer.close()
        await self.writer.wait_closed()

    async def create_mediator(self):
        name = f'{self.parent.adaptor.name}.mediator_{self.id}'
        msg = self.parent.adaptor.get_msg('create_actor', {'class_desc': mediator.Mediator, 'name': name})
        answer = await self.parent.adaptor.ask(msg)
        if answer.command != 'actor_is_created':
            return None
        msg = self.parent.adaptor.get_msg('set_params', {'params': [{'name': 'writer', 'value': self.writer}]}, name)
        await self.parent.adaptor.send(msg)
        return name

    async def create_convertor(self):
        name = f'{self.parent.adaptor.name}.convertor_{self.id}'
        msg = self.parent.adaptor.get_msg('create_actor', {'class_desc': self.parent.convertor_desc, 'name': name})
        msg.recipient = self.parent.balancer
        answer = await self.parent.adaptor.ask(msg)
        if answer.command != 'actor_is_created':
            return None
        self.parent.adaptor.add_to_cache(answer.body['node'], answer.body['entity'])
        body = {'params': [
            {'name': 'mediator', 'value': {'node': self.parent.adaptor.get_node(), 'entity': self.mediator}},
            {'name': 'consumer', 'value': self.parent.router}]}
        msg = self.parent.adaptor.get_msg('set_params', body, name)
        await self.parent.adaptor.ask(msg)
        return name
