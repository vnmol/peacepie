import asyncio
import os
import subprocess
from pathlib import Path

from simple_fastapi_dashboard import zmq_server


class SimpleFastapiActor:

    def __init__(self):
        self.adaptor = None
        self.port = None
        self.page_size = None
        self._proc = None
        self._zmq_server = None

    async def exit(self):
        if self._proc.poll() is None:  # Процесс все еще запущен
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        await self._zmq_server.exit()

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else None
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        elif command == 'stop':
            await self.stop(sender)
        elif command == 'get_base_dir':
            await self.get_base_dir(sender)
        elif command == 'get_params':
            await self.get_params(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        self.port = int(os.environ.get('PORT', self.port))
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))

    async def start(self, recipient):
        class_desc = {'requires_dist': 'simple_fastapi_dashboard', 'class': 'Dummy'}
        for i in range(25):
            body = {'class_desc': class_desc, 'name': f'dummy_{i:02d}'}
            await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 60)
        await self.start_zmq_server()
        cwd = os.path.dirname(__file__)
        log_config = self.adaptor.adjust_log_config(cwd, __package__)
        env = os.environ.copy()
        env['zmq_port'] = str(self._zmq_server.port)
        env['peacepie_path'] = self.adaptor.get_package_path()
        env['peacepie_serializer'] = self.adaptor.get_serializer_desc()
        self._proc = subprocess.Popen(
            [
                'python', '-m', 'uvicorn',
                'fastapi_server:app',
                '--host', '0.0.0.0',
                '--port', '8000',
                '--log-config', log_config
            ],
            cwd=cwd,
            env=env
        )
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('is_started', None, recipient))

    async def stop(self, recipient):
        self._proc.terminate()
        self._proc = None
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('is_stopped', None, recipient))

    async def get_base_dir(self, recipient):
        if not recipient:
            return
        body = {'path': str(Path(self.adaptor.get_param('browser_base_dir')).resolve())}
        await self.adaptor.send(self.adaptor.get_msg('base_dir', body, recipient))

    async def get_params(self, recipient):
        if not recipient:
            return
        body = {'params': [{'name': 'page_size', 'value': self.page_size}]}
        await self.adaptor.send(self.adaptor.get_msg('params', body, recipient))

    async def start_zmq_server(self):
        self._zmq_server = zmq_server.ZmqServer(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self._zmq_server.run(queue))
        await asyncio.wait_for(queue.get(), timeout=4)
