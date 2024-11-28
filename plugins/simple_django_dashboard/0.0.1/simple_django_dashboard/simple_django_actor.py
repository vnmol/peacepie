import asyncio
import logging
import os
import subprocess

from simple_django_dashboard import zmq_server

RESOURCES_PATH = 'resources'
DJANGO_COMMON_PATH = 'django_dir'
DJANGO_PROJECT_NAME = 'simple_django_site'


class SimpleDjangoActor:

    def __init__(self):
        self.adaptor = None
        self.path = os.path.join(os.path.dirname(__file__), f'{RESOURCES_PATH}/{DJANGO_COMMON_PATH}')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{DJANGO_PROJECT_NAME}.settings')
        self.zmq_server = None
        self.django = None

    async def exit(self):
        alias_name = self.adaptor.get_alias()
        await self.zmq_server.exit()
        if self.django:
            self.django.terminate()
            try:
                self.django.wait(timeout=4)
                logging.info(f'{alias_name}: Django({self.django.pid}) is closed')
            except subprocess.TimeoutExpired:
                self.django.kill()
                self.django.wait()
                logging.info(f'{alias_name}: Django({self.django.pid}) is killed')

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else None
        sender = msg.get('sender')
        if command == 'start':
            await self.start(body, sender)
        else:
            return False
        return True

    async def start(self, body, recipient):
        await self.start_zmq_server()
        self.django = subprocess.Popen(
            args=['daphne', '-b', 'localhost', '-p', f'{body.get("port")}', 'simple_django_site.asgi:application'],
            cwd=self.path
        )
        if recipient:
            if self.django:
                await self.adaptor.send(self.adaptor.get_msg('django_is_started', None, recipient))
            else:
                await self.adaptor.send(self.adaptor.get_msg('django_is_not_started', None, recipient))

    async def start_zmq_server(self):
        self.zmq_server = zmq_server.ZmqServer(self)
        queue = asyncio.Queue()
        asyncio.get_running_loop().create_task(self.zmq_server.run(queue))
        ans = await asyncio.wait_for(queue.get(), timeout=4)
        path = f'{self.path}/{DJANGO_PROJECT_NAME}'
        with open(f'{path}/settings.py', 'a', encoding='utf-8') as file:
            file.write(f'\n\nDASHBOARD_PEACEPIE_PATH = {self.adaptor.get_package_path()}\n')
            file.write(f'DASHBOARD_PEACEPIE_SERIALIZATOR = {self.adaptor.get_serializer_desc()}\n')
            file.write(f'DASHBOARD_ZMQ_SERVER_PORT = {self.zmq_server.port}\n')
            file.write(f'DASHBOARD_HOST_IP = \'{self.adaptor.get_param("ip")}\'\n')
