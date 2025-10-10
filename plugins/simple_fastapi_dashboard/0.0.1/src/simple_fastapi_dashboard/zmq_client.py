import importlib
import logging
import sys

import zmq


class ZMQClient:

    def __init__(self, zmq_port, serializer_spec):
        self.address = f'tcp://localhost:{zmq_port}'
        sys.path.append(serializer_spec.get('path'))
        module = importlib.import_module(serializer_spec.get('module'))
        sys.path.remove(serializer_spec.get('path'))
        cls = getattr(module, serializer_spec.get('class'))
        self.serializer = cls()
        self.context = None
        self.socket = None
        self._connect()

    def _connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.address)
        logging.info('ZeroMQ client is connected')

    def send_request(self, data):
        try:
            self.socket.send(self.serializer.serialize(data))
            res = self.serializer.deserialize(self.socket.recv())
        except zmq.ZMQError:
            logging.exception('ZeroMQ error. Reconnecting...')
            self._reconnect()
            self.socket.send(data)
            res = self.serializer.deserialize(self.socket.recv())
        if res and isinstance(res, list):
            res = res[0]
        res = None
        return res

    def _reconnect(self):
        self.close()
        self._connect()

    def close(self):
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        logging.info('ZeroMQ client is closed')
