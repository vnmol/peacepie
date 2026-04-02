import atexit
import importlib
import logging
import os
import sys

import zmq

from core import log_util

client = None


def init():
    global client
    client = ZMQClient()
    atexit.register(client.close)
    client.connect()


class ZMQClient:

    def __init__(self):
        self.address = f'tcp://0.0.0.0:{os.getenv("zmq_port")}'
        module_name, class_name = os.getenv('peacepie_serializer').split('|')
        sys.path.append(os.getenv('peacepie_path'))
        module = importlib.import_module(module_name)
        sys.path.remove(os.getenv('peacepie_path'))
        cls = getattr(module, class_name)
        self.serializer = cls()
        self.context = None
        self.socket = None

    def connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.address)
        logging.info('ZeroMQ client is connected')

    def ask(self, data):
        try:
            self.socket.send(self.serializer.serialize(data))
            logging.debug(f'ZeroMQ client transferred: {log_util.format_msg(data)}')
            res = self.serializer.deserialize(self.socket.recv())
            logging.debug(f'ZeroMQ client obtained: {log_util.format_msg(res)}')
        except zmq.ZMQError:
            logging.exception('ZeroMQ error. Reconnecting...')
            self._reconnect()
            self.socket.send(data)
            logging.debug(f'ZeroMQ client transferred: {log_util.format_msg(data)}')
            res = self.serializer.deserialize(self.socket.recv())
            logging.debug(f'ZeroMQ client obtained: {log_util.format_msg(res)}')
        if res and isinstance(res, list):
            res = res[0]
        return res

    def _reconnect(self):
        self.close()
        self.connect()

    def close(self):
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        logging.info('ZeroMQ client is closed')
