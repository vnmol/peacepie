import os

from django.apps import AppConfig


from .zmq_client import ZMQClient

ZMQ_SERVER_PORT = 'ZMQ_SERVER_PORT'


class DashboardConfig(AppConfig):
    name = 'dashboard'
