
class ComplexName:

    @staticmethod
    def parse_name(name):
        tokens = name.split('.')
        if len(tokens) != 3:
            return None
        res = ComplexName(tokens[0], tokens[1], tokens[2])
        return res

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

    def __eq__(self, other):
        if isinstance(other, ComplexName):
            return (self.host_name == other.host_name and
                    self.process_name == other.process_name and
                    self.actor_name == other.actor_name)
        return False

    def __hash__(self):
        return hash((self.host_name, self.process_name, self.actor_name))


class InterAddress:

    def __init__(self, host, port, authkey):
        self.host = host
        self.port = port
        self.authkey = authkey
