import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class AbsLoopinData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_ABS_LOOPIN_DATA, srl)
        self.lin = None
        self.lis = None

    def decode(self, payload, pos):
        val, = struct.unpack_from("<H", payload, pos)
        pos += 2
        self.lis = val & 0xF
        self.lin = val >> 4
        return pos

    def decode_with_print(self, payload, pos):
        val, = struct.unpack_from("<H", payload, pos)
        value = 'LIN(Loop In Number), LIS(Loop In State)'
        print(" " * 12 + f'{payload[pos]:02X} {payload[pos+1]:02X}'.ljust(16) + value)
        pos += 2
        self.lis = val & 0xF
        self.lin = val >> 4
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack('<H', (self.lin << 4) | (self.lis & 0xF))
        return res


if __name__ == "__main__":
    origin = AbsLoopinData(None)
    origin.lin = random.randint(0, 0xFFF)
    origin.lis = random.randint(0, 0xF)
    pl = origin.encoding()
    duplicate = AbsLoopinData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
