import asyncio
import logging

from peacepie import msg_factory


class TickerAdmin:

    def __init__(self):
        self.tickers = {}
        self.ticker_index = 0

    def add_ticker(self, queue, period, count, name, command):
        if not name:
            name = f'ticker_{self.ticker_index}'
            self.ticker_index += 1
        if not command:
            command = 'tick'
        self.tickers[name] = asyncio.get_running_loop().create_task(self.tick(queue, period, count, command))
        return name

    def remove_ticker(self, name):
        task = self.tickers.get(name)
        if not task:
            return
        task.cancel()
        del self.tickers[name]

    def is_ticker_exists(self, name):
        return name in self.tickers.keys()

    async def tick(self, queue, period, count, command):
        while True:
            await queue.put(msg_factory.get_msg(command))
            await asyncio.sleep(period)
            if count:
                count -= 1
                if count == 0:
                    break
