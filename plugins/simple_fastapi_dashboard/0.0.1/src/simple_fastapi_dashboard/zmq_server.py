import asyncio

import zmq
import zmq.asyncio
import logging


class ZmqServer:

    def __init__(self, parent):
        self.parent = parent
        self.serializer = parent.adaptor.get_serializer()
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REP)
        self.port = 0
        logging.info(f'{self.parent.adaptor.get_alias(self)} is created')

    async def exit(self):
        if not self.socket.closed:
            self.socket.close()
            logging.info(f'{self.parent.adaptor.get_alias(self)} on port {self.port} is closed')
        self.context.term()
        logging.info(f'{self.parent.adaptor.get_alias(self)} is shutdown')

    async def run(self, queue):
        try:
            self.socket.bind("tcp://*:0")
            self.port = self.socket.getsockopt(zmq.LAST_ENDPOINT).decode("utf-8").split(":")[-1]
            if queue:
                await queue.put(self.parent.adaptor.get_msg('ready'))
            logging.info(f'{self.parent.adaptor.get_alias(self)} is started on port {self.port}')
            await self.server_handle()
        except Exception as ex:
            logging.exception(ex)

    async def server_handle(self):
        adaptor = self.parent.adaptor
        while True:
            try:
                msgs = self.serializer.deserialize(await asyncio.wait_for(self.socket.recv(), 300))
                for msg in msgs:
                    logging.debug(f'{adaptor.get_alias(self)} obtained: {adaptor.format_msg(msg)}')
                    tp = msg.get('type')
                    body = msg.get('body')
                    recipient = msg.get('recipient')
                    if recipient is None:
                        match msg.get('command'):
                            case 'get_base_dir' | 'get_params':
                                recipient = self.parent.adaptor.name
                            case _:
                                recipient = self.parent.adaptor.get_head_addr()
                    try:
                        timeout = int(msg.get('timeout')) if msg.get('timeout') else 4
                    except Exception as e:
                        logging.exception(e)
                        timeout = 4
                    query = self.parent.adaptor.get_msg(msg.get('command'), body, recipient, user=msg.get('user'))
                    if tp == 'send':
                        await self.parent.adaptor.send(query)
                        res = 'The message is sent'
                    else:
                        res = await self.parent.adaptor.ask(query, timeout)
                    await self.socket.send(self.serializer.serialize(res))
                    logging.debug(f'{adaptor.get_alias(self)} transferred: {adaptor.format_msg(res)}')
            except TimeoutError:
                pass
