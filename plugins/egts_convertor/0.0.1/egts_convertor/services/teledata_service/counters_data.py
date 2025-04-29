import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class CountersData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_COUNTERS_DATA, srl)
        self.cn = {}

    def decode(self, payload, pos):
        cfe, = struct.unpack_from("<B", payload, pos)
        pos += 1
        for i in range(8):
            if cfe & 0x01:
                self.cn[i] = int.from_bytes(payload[pos:pos + 3], 'little')
                pos += 3
            cfe = cfe >> 1
        return pos

    def decode_with_print(self, payload, pos):
        cfe, = struct.unpack_from("<B", payload, pos)
        value = "CFE (Counter Field Exists) {"
        cfe_for_print = cfe
        for i in range(8):
            if cfe_for_print & 0x01:
                value += f' CFE{i+1}'
            cfe_for_print = cfe_for_print >> 1
        value += " }"
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + value)
        pos += 1
        for i in range(8):
            if cfe & 0x01:
                self.cn[i] = int.from_bytes(payload[pos:pos + 3], 'little')
                value = f"{payload[pos]:02X} {payload[pos+1]:02X} {payload[pos+2]:02X}".ljust(16)
                print(" " * 12 + value + f"CN{i+1} (Counter {i+1})")
                pos += 3
            cfe = cfe >> 1
        print()
        return pos

    def encoding(self):
        res = bytearray()
        cfe = 0
        for key in self.cn.keys():
            cfe |= 1 << key
        res += struct.pack("<B", cfe)
        for value in self.cn.values():
            res += value.to_bytes(3, 'little')
        return res


if __name__ == "__main__":
    origin = CountersData(None)
    duplicate = CountersData(None)
    for flag in range(0x100):
        origin.clear()
        for i in range(8):
            if flag & (0x01 << i):
                origin.cn[i] = random.getrandbits(8)
        pl = origin.encoding()
        duplicate.clear()
        duplicate.decode(pl, 0)
        assert origin == duplicate
