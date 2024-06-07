import logging

from simple_tcp import tcp_server


class EmbeddedChannel:

    def __init__(self, parent, reader, writer):
        self.parent = parent
        self.id = next(tcp_server.gen_id)
        self.name = f'channel_{self.id}'
        self.reader = reader
        self.writer = writer
        self.convertor = None
        self.convertor_name = f'{self.parent.adaptor.name}.convertor_{self.id}'
        self.cumulative_commands = {}

    async def handle(self):
        await self.create_convertor()
        logging.info(f'{self.parent.adaptor.get_alias(self)} Channel is opened')
        while True:
            if not self.parent.adaptor.is_running or self.reader.at_eof():
                break
            try:
                data = await self.reader.read(255)
                # logging.debug(f'{self.parent.adaptor.get_alias(self)} THE DATA IS RECEIVED')
                await self.convertor.handle(self.parent.adaptor.get_msg('raw_data', data, self.convertor_name))
            except Exception as ex:
                logging.exception(ex)
        self.writer.close()
        await self.writer.wait_closed()

    async def create_convertor(self):
        self.convertor = self.parent.convertor_class()
        if not hasattr(self.convertor, 'adaptor'):
            txt = f'The performer "{self.convertor_name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.convertor.adaptor = self
        body = {'params': [{'name': 'mediator', 'value': '_embedded'},
                           {'name': 'consumer', 'value': self.parent.consumer}]}
        msg = self.parent.adaptor.get_msg('set_params', body, sender='_parent')
        try:
            await self.convertor.handle(msg)
        except Exception as e:
            logging.exception(e)

    async def send(self, msg):
        if msg.get('recipient') == '_parent':
            return
        if msg.get('recipient') == '_embedded':
            self.writer.write(msg.get('body'))
            await self.writer.drain()
            # logging.debug(f'{self.parent.adaptor.get_alias(self)} THE DATA ARE SENT')
        else:
            await self.parent.adaptor.send(msg, self)

    def get_msg(self, command, body=None, recipient=None, sender=None):
        return self.parent.adaptor.get_msg(command, body, recipient, sender)

    def json_loads(self, jsn):
        return self.parent.adaptor.json_loads(jsn)

    def json_dumps(self, jsn):
        return self.parent.adaptor.json_dumps(jsn)

    def add_to_cache(self, node, entity):
        if node == '_embedded':
            return
        self.parent.adaptor.add_to_cache(node, entity)
