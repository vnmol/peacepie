import asyncio
import os

DEFAULT_PERIOD = 60


class SimpleScriptCommanderReader:

    def __init__(self):
        self.adaptor = None
        self.consumer = None
        self.script_path = 'scripts'
        self.period = DEFAULT_PERIOD
        self.task = None
        self.scripts = set()

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'start':
            await self.start(msg)
        elif command == 'stop':
            await self.stop()
        elif command == 'set_params':
            await self.set_params(msg)
        else:
            return False
        return True

    async def start(self, msg):
        if msg.get('body'):
            await self.set_params(msg)
        self.adaptor.makedir(self.script_path, True)
        self.task = asyncio.get_running_loop().create_task(self.run())

    async def stop(self):
        if not self.task:
            return
        await self.task.cancel()
        self.task = None

    async def set_params(self, msg):
        body = msg.get('body')
        if not body:
            return
        params = body.get('params')
        if not params:
            return
        for param in params:
            if not param.get('name') or not param.get('value'):
                continue
            if param['name'] == 'consumer':
                self.consumer = param['value']
            elif param['name'] == 'script_path':
                self.script_path = param['value']
            elif param['name'] == 'period':
                try:
                    self.period = int(param['value'])
                except ValueError:
                    self.period = DEFAULT_PERIOD

    async def run(self):
        while True:
            for filename in os.listdir(self.script_path):
                if filename in self.scripts:
                    continue
                await self.process(filename)
                self.scripts.add(filename)
            await asyncio.sleep(self.period)

    async def process(self, filename):
        with open(f'{self.script_path}/{filename}', 'r') as f:
            for line in f:
                message = self.adaptor.json_loads(line)
                if not message:
                    continue
                msg = self.adaptor.get_msg(message.get('command'), message.get('body'), self.consumer)
                await self.adaptor.send(msg)



