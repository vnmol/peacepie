import random

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class AbsCntrData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_ABS_CNTR_DATA, srl)
        self.cn = None
        self.cnv = None

    def decode(self, payload, pos):
        self.cn = payload[pos]
        pos += 1
        self.cnv = int.from_bytes(payload[pos:pos + 3], 'little')
        pos += 3
        return pos

    def decode_with_print(self, payload, pos):
        self.cn = payload[pos]
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "CN (Counter  Number)")
        pos += 1
        self.cnv = int.from_bytes(payload[pos:pos + 3], 'little')
        value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X}".ljust(16)
        print(" " * 12 + value + "CNV (Counter Value)")
        pos += 3
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res.append(self.cn)
        res += self.cnv.to_bytes(3, 'little')
        return res

if __name__ == "__main__":
    origin = AbsCntrData(None)
    origin.cn = random.randint(0, 0xFF)
    origin.cnv = random.randint(0, 0xFFFFFF)
    pl = origin.encoding()
    duplicate = AbsCntrData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
