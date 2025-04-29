import struct


class SubRecord:

    def __init__(self, parent, srt, srl):
        self.parent = parent
        self.srt = srt
        self.srl = srl
        self._fields = {name for name, value in vars(self).items() if not(name.startswith('_') or callable(value))}

    def __repr__(self):
        return ', '.join(f'{name}={value!r}' for name, value in vars(self).items()
            if not(name.startswith('_') or callable(value) or name in self._fields))

    def clear(self):
        for name, value in vars(self).items():
            if not name.startswith('_') and not callable(value):
                if type(value) is dict:
                    setattr(self, name, {})
                elif type(value) is list:
                    setattr(self, name, [])
                else:
                    setattr(self, name, None)

    def __eq__(self, other):
        return compare(self, other)

    def encode(self):
        res = bytearray()
        body = self.encoding()
        res += struct.pack('<BH', self.srt, len(body))
        res += body
        return res

    def encoding(self):
        return b''

    def build_response(self, record):
        pass


def compare(obj1, obj2):
    if type(obj1) != type(obj2):
        return False
    if obj1 is None and obj2 is None:
        return True
    if isinstance(obj1, (int, float, str, bool)):
        return obj1 == obj2
    if isinstance(obj1, dict):
        if len(obj1) != len(obj2):
            return False
        for key in obj1:
            if key not in obj2:
                return False
            if not compare(obj1[key], obj2[key]):
                return False
        return True
    if isinstance(obj1, (list, tuple, set)):
        if len(obj1) != len(obj2):
            return False
        if isinstance(obj1, set):
            return obj1 == obj2
        return all(compare(x, y) for x, y in zip(obj1, obj2))
    if hasattr(obj1, '__dict__') and hasattr(obj2, '__dict__'):
        return compare(obj1.__dict__, obj2.__dict__)
    return obj1 == obj2
