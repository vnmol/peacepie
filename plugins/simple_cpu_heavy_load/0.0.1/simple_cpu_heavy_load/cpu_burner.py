import asyncio
import time

from prompt_toolkit.key_binding.bindings.named_commands import previous_history


class CpuBurner:

    def __init__(self):
        self.adaptor = None
        self.remaining_time = 60

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start()
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self):
        print('BEFORE', self.adaptor.get_caller_info())
        await asyncio.to_thread(self.heavy_load)
        print('AFTER', self.adaptor.get_caller_info())

    def heavy_load(self):
        previous = time.time()
        while True:
            current = time.time()
            self.remaining_time -= current - previous
            previous = current
            if self.remaining_time <= 0:
                return


