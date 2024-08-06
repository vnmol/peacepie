import logging

from simple_networking import mediator


class Channel:

    def __init__(self, parent, reader, writer):
        self.parent = parent
        self.ch_id = self.parent.adaptor.series_next(self.parent.adaptor.name)
        self.name = f'channel_{self.ch_id}'
        self.start_queue = None
        self.mediator = None
        self.convertor = None
        self.reader = reader
        self.writer = writer
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
        self.start_queue = queue
        self.mediator = await self.create_mediator()
        self.convertor = await self.create_convertor()
        if self.start_queue:
            await self.start_queue.put(self.parent.adaptor.get_msg('channel_is_opened'))
        log = f'{self.parent.adaptor.get_alias(self)} connected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        logging.info(log)
        while True:
            try:
                data = await self.reader.read(255)
                if self.reader.at_eof():
                    break
                msg = self.parent.adaptor.get_msg('received_from_channel', data, self.convertor)
                await self.parent.adaptor.send(msg, self)
            except Exception as ex:
                logging.exception(ex)
        await self.parent.adaptor.ask(self.parent.adaptor.get_msg('remove_actor', {'name': self.mediator}))
        await self.parent.adaptor.ask(self.parent.adaptor.get_msg('remove_actor', {'name': self.convertor}))
        log = f'{self.parent.adaptor.get_alias(self)} disconnected '
        log += f'{self.writer.get_extra_info("sockname")}<=>{self.writer.get_extra_info("peername")}'
        logging.info(log)

    async def create_mediator(self):
        name = f'{self.parent.adaptor.name}.mediator_{self.ch_id}'
        msg = self.parent.adaptor.get_msg('create_actor', {'class_desc': mediator.Mediator, 'name': name})
        ans = await self.parent.adaptor.ask(msg)
        if ans.get('command') != 'actor_is_created':
            return None
        body = {'params': [{'name': 'writer', 'value': self.writer}]}
        msg = self.parent.adaptor.get_msg('set_params', body, name)
        await self.parent.adaptor.send(msg)
        body = {'commands': list(self.not_log_commands)}
        await self.parent.adaptor.send(self.parent.adaptor.get_msg('not_log_commands_set', body, name))
        return name

    async def create_convertor(self):
        name = f'{self.parent.adaptor.name}.convertor_{self.ch_id}'
        msg = self.parent.adaptor.get_msg('create_actor', {'class_desc': self.parent.convertor_desc, 'name': name})
        ans = await self.parent.adaptor.ask(msg)
        if ans.get('command') != 'actor_is_created':
            return None
        body = {'params': [
            {'name': 'mediator', 'value': self.mediator},
            {'name': 'consumer', 'value': self.parent.consumer}]}
        msg = self.parent.adaptor.get_msg('set_params', body, name)
        await self.parent.adaptor.ask(msg)
        body = {'commands': list(self.not_log_commands)}
        await self.parent.adaptor.send(self.parent.adaptor.get_msg('not_log_commands_set', body, name))
        return name

    async def send_to_channel(self, msg):
        if not self.convertor:
            timeout = msg.get('timeout') if msg.get('timeout') else 4
            self.parent.adaptor.start_timer(self.start_queue, msg.get('mid'), timeout)
            ans = await self.start_queue.get()
            if ans.get('command') != 'channel_is_opened':
                if msg.get('sender'):
                    await self.parent.adaptor.send(ans)
                return
        msg['recipient'] = self.convertor
        await self.parent.adaptor.send(msg)
