import asyncio
import logging


class SimpleTcpClient:

    def __init__(self):
        self.adaptor = None
        self.inet_addr = None
        self.convertor_desc = None
        self.convertor = None
        self.is_on_demand = True
        self.is_active = False
        self.writer = None

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'navi_data':
            await self.navi_data(msg)
        elif command == 'raw_data':
            await self.raw_data(msg)
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        elif command == 'start':
            await self.start(msg.get('sender'))
        else:
            return False
        return True

    async def navi_data(self, msg):
        msg['recipient'] = self.convertor
        await self.adaptor.send(msg)

    async def raw_data(self, msg):
        if not self.is_active:
            asyncio.get_running_loop().create_task(self.handle_connection())
            await asyncio.sleep(0.1)
        if not self.writer:
            await asyncio.sleep(1)
        if not self.writer:
            return
        self.writer.write(msg.get('body'))
        await self.writer.drain()
        logging.debug(f'{self.adaptor.get_alias(self)} THE DATA ARE SENT')

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'inet_addr':
                self.inet_addr = value
            elif name == 'convertor_desc':
                self.convertor_desc = value
            elif name == 'is_on_demand':
                self.is_on_demand = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        await self.create_convertor()
        if not self.is_on_demand:
            asyncio.get_running_loop().create_task(self.handle_connection())
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('started', recipient=recipient))

    async def create_convertor(self):
        name = f'{self.adaptor.name}.convertor'
        msg = self.adaptor.get_msg('create_actor', {'class_desc': self.convertor_desc, 'name': name})
        ans = await self.adaptor.ask(msg)
        if ans.get('command') != 'actor_is_created':
            return None
        body = {'params': [{'name': 'mediator', 'value': self.adaptor.get_self_addr()}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, ans.get('body')))
        self.convertor = ans.get('body')

    async def handle_connection(self):
        self.is_active = True
        logging.info(self.adaptor.get_alias() + ' Channel is active')
        reader = None
        while True:
            try:
                reader, self.writer = await asyncio.open_connection(self.inet_addr['host'], self.inet_addr['port'])
                logging.info(self.adaptor.get_alias() + ' Channel is opened')
            except Exception as ex:
                logging.exception(ex)
            while reader:
                if not self.adaptor.is_running or reader.at_eof():
                    break
                try:
                    data = await reader.read(255)
                    logging.debug(f'{self.adaptor.get_alias(self)} THE DATA ARE RECEIVED')
                    await self.adaptor.send(self.adaptor.get_msg('raw_data', data, self.convertor))
                except Exception as ex:
                    logging.exception(ex)
                    reader = None
            if self.writer:
                logging.info(self.adaptor.get_alias() + ' Channel is closed')
                self.writer.close()
                await self.writer.wait_closed()
            self.writer = None
            if self.is_on_demand:
                self.is_active = False
                logging.info(self.adaptor.get_alias() + ' Channel is inactive')
                return
            else:
                await asyncio.sleep(10)
