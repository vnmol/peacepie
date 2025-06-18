import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class DispatcherIdentity(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_DISPATCHER_IDENTITY, srl)
        self.dt = None
        self.did = None
        self.dscr = None

    def init(self):
        self.dt = 1
        self.did = 1

    def decode(self, payload, pos):
        self.dt, self.did = struct.unpack_from("<BI", payload, pos)
        pos += 5
        if self.srl > 5:
            l = self.srl - 5
            self.dscr = payload[pos:pos+l].decode(constants.DEFAULT_CHARSET)
            pos += l
        return pos

    def decode_with_print(self, payload, pos):
        self.dt, self.did = struct.unpack_from("<BI", payload, pos)
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "DT (Dispatcher Type)")
        buf = payload[pos + 1 :pos + 5]
        value = " ".join([format(byte, "02X") for byte in buf])
        print(" " * 12 + value.ljust(16) + "DID (Dispatcher ID)")
        pos += 5
        if self.srl > 5:
            l = self.srl - 5
            buf = payload[pos:pos+l]
            self.dscr = buf.decode(constants.DEFAULT_CHARSET)
            value = " ".join([format(byte, "02X") for byte in buf])
            print(" " * 12 +  value + f"   DSCR (Description)={self.dscr}")
            pos += l
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<BI", self.dt, self.did)
        if self.dscr:
            res += self.dscr.encode(constants.DEFAULT_CHARSET)
        return res


if __name__ == "__main__":
    hex_chars = '0123456789ABCDEF'
    dscr = ''.join(random.choices(hex_chars, k=random.randint(5, 15)))
    origin = DispatcherIdentity(None, 5 + len(dscr))
    origin.dt = random.randint(0, 0xFF)
    origin.did = random.randint(0, 0xFFFFFFFF)
    origin.dscr = dscr
    pl = origin.encoding()
    duplicate = DispatcherIdentity(None, 5 + len(dscr))
    duplicate.decode(pl, 0)
    assert origin == duplicate
