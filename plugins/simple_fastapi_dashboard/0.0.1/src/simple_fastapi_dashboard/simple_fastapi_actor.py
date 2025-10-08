import asyncio
import multiprocessing
from . import fastapi_server, zmq_server


class SimpleFastapiActor:

    def __init__(self):
        self.adaptor = None
        self.port = None
        self.zmq_server = None
        self.server_process = None

    async def exit(self):
        await self.zmq_server.exit()
        if self.server_process and self.server_process.is_alive():
            self.server_process.terminate()
            self.server_process.join(timeout=5)
            if self.server_process.is_alive():
                self.server_process.kill()

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else None
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        await self.start_zmq_server()
        self.server_process = multiprocessing.Process(
            target=fastapi_server.run_server,
            args=(self.port, self.zmq_server.port, self.adaptor.get_serializer_spec())
        )
        self.server_process.start()
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('fastapi_is_started', None, recipient))

    async def start_zmq_server(self):
        self.zmq_server = zmq_server.ZmqServer(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.zmq_server.run(queue))
        await asyncio.wait_for(queue.get(), timeout=4)
