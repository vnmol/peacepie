import logging


class EmbeddedChannel:

    def __init__(self, parent, reader, writer):
        self.parent = parent
        self.ch_id = self.parent.adaptor.series_next(self.parent.adaptor.name)
        self.name = f'channel_{self.ch_id}'
        self.reader = reader
        self.writer = writer
        self.convertor = None
        self.not_log_commands = set()
        self.cumulative_commands = {}
        logging.info(f'{self.parent.adaptor.get_alias(self)} is created')

    async def exit(self):
        log = f'{self.parent.adaptor.get_alias(self)} disconnected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        self.writer.close()
        await self.writer.wait_closed()
        logging.info(log)

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def handle(self, queue):
        await self.create_convertor()
        if queue:
            await queue.put(self.parent.adaptor.get_msg('channel_is_opened'))
        log = f'{self.parent.adaptor.get_alias(self)} connected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        logging.info(log)
        while True:
            try:
                data = await self.reader.read(255)
                if self.reader.at_eof():
                    break
                msg = self.parent.adaptor.get_msg('received_from_channel', data)
                await self.convertor.handle(msg)
            except Exception as ex:
                logging.exception(ex)
        log = f'{self.parent.adaptor.get_alias(self)} disconnected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        logging.info(log)

    async def create_convertor(self):
        name = f'{self.parent.adaptor.name}.convertor_{self.ch_id}'
        self.convertor = self.parent.convertor_class()
        if not hasattr(self.convertor, 'adaptor'):
            txt = f'The performer "{name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.convertor.adaptor = self
        body = {'params': [
            {'name': 'mediator', 'value': '_mediator'},
            {'name': 'consumer', 'value': self.parent.consumer}]}
        msg = self.parent.adaptor.get_msg('set_params', body, name, sender='_parent')
        await self.convertor.handle(msg)

    async def send_to_channel(self, msg):
        await self.convertor.handle(msg)

    async def send(self, msg):
        if msg.get('recipient') == '_parent':
            return
        if msg.get('recipient') == '_mediator':
            self.writer.write(msg.get('body'))
            await self.writer.drain()
        else:
            await self.parent.adaptor.send(msg, self)

    def get_msg(self, command, body=None, recipient=None, sender=None):
        return self.parent.adaptor.get_msg(command, body, recipient, sender)

    def json_dumps(self, jsn):
        return self.parent.adaptor.json_dumps(jsn)

    def json_loads(self, jsn):
        return self.parent.adaptor.json_loads(jsn)
