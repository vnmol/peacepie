import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class TestIdData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_TEST_ID_DATA, srl)
        self.id = None

    def set_id(self, id):
        self.id = id

    def get_id(self):
        return self.id

    def decode(self, payload, pos):
        self.id, = struct.unpack_from("<I", payload, pos)
        pos += 4
        return pos

    def decode_with_print(self, payload, pos):
        self.id, = struct.unpack_from("<I", payload, pos)
        buf = payload[pos:pos + 4]
        value = " ".join([format(byte, "02X") for byte in buf]).ljust(16)
        print(" " * 12 + value + "ID")
        pos += 4
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<I", self.id)
        return res

if __name__ == "__main__":
    origin = TestIdData(None)
    origin.id = random.randint(0, 65535)
    pl = origin.encoding()
    duplicate = TestIdData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
