import random

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class AbsAnSensData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_ABS_AN_SENS_DATA, srl)
        self.asn = None
        self.asv = None

    def decode(self, payload, pos):
        self.asn = payload[pos]
        pos += 1
        self.asv = int.from_bytes(payload[pos:pos + 3], 'little')
        pos += 3
        return pos

    def decode_with_print(self, payload, pos):
        self.asn = payload[pos]
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "ASN (Analog Sensor Number)")
        pos += 1
        self.asv = int.from_bytes(payload[pos:pos + 3], 'little')
        value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X}".ljust(16)
        print(" " * 12 + value + "ASV (Analog Sensor Value)")
        pos += 3
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res.append(self.asn)
        res += self.asv.to_bytes(3, 'little')
        return res

if __name__ == "__main__":
    origin = AbsAnSensData(None)
    origin.asn = random.randint(0, 0xFF)
    origin.asv = random.randint(0, 0xFFFFFF)
    pl = origin.encoding()
    duplicate = AbsAnSensData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
