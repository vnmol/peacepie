import importlib
import sys

import zmq
from django.conf import settings

class ZMQClient:
    def __init__(self):
        self.address = f'tcp://localhost:{settings.DASHBOARD_ZMQ_SERVER_PORT}'
        module_name, class_name = settings.DASHBOARD_PEACEPIE_SERIALIZATOR.split('|')
        sys.path.append(settings.DASHBOARD_PEACEPIE_PATH)
        module = importlib.import_module(module_name)
        sys.path.remove(settings.DASHBOARD_PEACEPIE_PATH)
        cls = getattr(module, class_name)
        self.serializer = cls()
        self.context = None
        self.socket = None
        self._connect()

    def _connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.address)
        print('ZeroMQ client is connected')

    def send_request(self, data):
        try:
            self.socket.send(self.serializer.serialize(data))
            res = self.serializer.deserialize(self.socket.recv())
        except zmq.ZMQError:
            print('ZeroMQ error. Reconnecting...')
            self._reconnect()
            self.socket.send(data)
            res = self.serializer.deserialize(self.socket.recv())
        if res and isinstance(res, list):
            res = res[0]
        return res

    def _reconnect(self):
        self.close()
        self._connect()

    def close(self):
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        print("ZeroMQ client is closed")
