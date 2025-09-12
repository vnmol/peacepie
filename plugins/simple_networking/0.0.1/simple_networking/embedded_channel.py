import logging


class EmbeddedChannel:

    def __init__(self, parent, reader, writer):
        self.parent = parent
        self.ch_id = self.parent.adaptor.series_next(self.parent.adaptor.name)
        self.name = f'channel_{self.ch_id}'
        self.inner_name = '_parent'
        self.start_queue = None
        self.reader = reader
        self.writer = writer
        self.convertor = None
        self.not_log_commands = set()
        self.cumulative_commands = {}
        logging.info(f'{self.parent.adaptor.get_alias(self)} is created')

    async def exit(self):
        log = f'{self.parent.adaptor.get_alias(self)} disconnected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        await self.close()
        if hasattr(self.convertor, 'exit'):
            await self.convertor.exit()
        logging.info(log)

    async def close(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as e:
            logging.exception(e)

    async def handle(self, queue):
        self.start_queue = queue
        log = f'{self.parent.adaptor.get_alias(self)} connected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        logging.info(log)
        await self.create_convertor()
        while True:
            try:
                data = await self.reader.read(255)
                if self.reader.at_eof():
                    break
                msg = self.parent.adaptor.get_msg('received_from_channel', data)
                await self.convertor.handle(msg)
            except Exception as ex:
                logging.exception(ex)
        if self.parent.adaptor.stop_event is None:
            log = f'{self.parent.adaptor.get_alias(self)} disconnected '
            log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
            await self.close()
            logging.info(log)

    async def create_convertor(self):
        name = f'{self.parent.adaptor.name}.convertor_{self.ch_id}'
        try:
            self.convertor = self.parent.convertor_class()
        except Exception as e:
            logging.exception(e)
        if not hasattr(self.convertor, 'adaptor'):
            txt = f'The performer "{name}" does not have the attribute "adaptor"'
            raise AttributeError(txt)
        self.convertor.adaptor = self
        body = {'params': [
            {'name': 'mediator', 'value': '_mediator'},
            {'name': 'consumer', 'value': self.parent.consumer},
            {'name': 'convertor_params', 'value': self.parent.convertor_params}
        ]}
        msg = self.parent.adaptor.get_msg('set_params', body, name, self.inner_name)
        await self.convertor.handle(msg)
        if self.not_log_commands:
            body = {'commands': list(self.not_log_commands)}
            msg = self.parent.adaptor.get_msg('not_log_commands_set', body, self.inner_name)
            await self.parent.adaptor.handle(msg)
        msg = self.parent.adaptor.get_msg('start', {'is_client': self.parent.is_client}, self.inner_name)
        await self.convertor.handle(msg)

    async def send_to_channel(self, msg):
        await self.convertor.handle(msg)

    async def send(self, msg):
        if msg.get('recipient') == '_parent':
            return
        if msg.get('recipient') == '_mediator':
            match msg.get('command'):
                case 'send_to_channel':
                    self.writer.write(msg.get('body'))
                    await self.writer.drain()
                case 'channel_is_opened':
                    if self.start_queue:
                        await self.start_queue.put(msg)
        else:
            await self.parent.adaptor.send(msg, self)

    def get_msg(self, command, body=None, recipient=None, sender=None):
        return self.parent.adaptor.get_msg(command, body, recipient, sender)

    def json_dumps(self, jsn):
        return self.parent.adaptor.json_dumps(jsn)

    def json_loads(self, jsn):
        return self.parent.adaptor.json_loads(jsn)

    def get_caller_info(self):
        return self.parent.adaptor.get_caller_info()
