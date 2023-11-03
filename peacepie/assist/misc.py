
class ComplexName:

    def __init__(self, host_name, process_name, actor_name):
        self.host_name = host_name
        self.process_name = process_name
        self.actor_name = actor_name

    def get_process_name(self):
        return f'{self.host_name}.{self.process_name}'

    def get_actor_name(self):
        return f'{self.host_name}.{self.process_name}.{self.actor_name}'

    def __repr__(self):
        return f'{self.host_name}:{self.process_name}:{self.actor_name}'


class InterAddress:

    def __init__(self, host, port, authkey):
        self.host = host
        self.port = port
        self.authkey = authkey
