import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class AbsDigSensData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_ABS_DIG_SENS_DATA, srl)
        self.dsn = None
        self.dsst = None

    def decode(self, payload, pos):
        val, = struct.unpack_from("<H", payload, pos)
        pos += 2
        self.dsst = val & 0xF
        self.dsn = val >> 4
        return pos

    def decode_with_print(self, payload, pos):
        val, = struct.unpack_from("<H", payload, pos)
        value = 'DSN(Digital Sensor Number), DSST(Digital Sensor State)'
        print(" " * 12 + f'{payload[pos]:02X} {payload[pos+1]:02X}'.ljust(16) + value)
        pos += 2
        self.dsst = val & 0xF
        self.dsn = val >> 4
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack('<H', (self.dsn << 4) | (self.dsst & 0xF))
        return res


if __name__ == "__main__":
    origin = AbsDigSensData(None)
    origin.dsn = random.randint(0, 0xFFF)
    origin.dsst = random.randint(0, 0xF)
    pl = origin.encoding()
    duplicate = AbsDigSensData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
