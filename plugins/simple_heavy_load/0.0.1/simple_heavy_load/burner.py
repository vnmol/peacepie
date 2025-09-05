import asyncio
import logging
import threading
import time


class Burner:

    def __init__(self):
        self.adaptor = None
        self.remaining_time = 60
        self._stop_event = threading.Event()

    async def exit(self):
        self._stop_event.set()

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
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
        await asyncio.to_thread(self.heavy_load, self._stop_event)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('finish', None, recipient))

    def heavy_load(self, stop_event):
        previous = time.time()
        flag = False
        while not stop_event.is_set():
            current = time.time()
            self.remaining_time -= current - previous
            previous = current
            if self.remaining_time <= 0:
                flag = True
                break
        if flag:
            logging.debug(f'{self.adaptor.get_alias(self)} completed successfully')
        else:
            logging.info(f'{self.adaptor.get_alias(self)} exited early')
