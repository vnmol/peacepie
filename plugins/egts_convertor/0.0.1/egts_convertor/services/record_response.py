import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class RecordResponse(SubRecord):

    def __init__(self, parent, srl):
        super().__init__(parent, constants.EGTS_SR_RECORD_RESPONSE, srl)
        self.crn =None
        self.rst = None

    def decode(self, payload, pos):
        self.crn, self.rst = struct.unpack_from("<HB", payload, pos)
        pos += 3
        return pos

    def decode_with_print(self, payload, pos):
        self.crn, self.rst = struct.unpack_from("<HB", payload, pos)
        print(" " * 12 + f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "CRN (Confirmed Record Number)")
        pos += 2
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + f"RST(Record Status)={constants.response_types.get(self.rst)}")
        pos += 1
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<HB", self.crn, self.rst)
        return res


if __name__ == "__main__":
    origin = RecordResponse(None, 0)
    origin.crn = random.randint(0, 0xFFFF)
    origin.rst = random.randint(0, 0xFF)
    payload = origin.encoding()
    duplicate = RecordResponse(None, 0)
    duplicate.decode(payload, 0)
    assert origin == duplicate
