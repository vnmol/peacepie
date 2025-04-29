import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class LoopinData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_LOOPIN_DATA, srl)
        self.lis = {}

    def decode(self, payload, pos):
        life = payload[pos]
        pos += 1
        val = 0
        mask = 1
        index = None
        for i in range(8):
            if life & mask:
                if index is None:
                    val = payload[pos]
                    index = i
                    self.lis[index] = val & 0xF
                else:
                    self.lis[i] = val >> 4
                    pos += 1
                    index = None
            mask = mask << 1
        if index:
            pos += 1
        return pos

    def decode_with_print(self, payload, pos):
        life = payload[pos]
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "LIFE (Loop In Field Exists)")
        pos += 1
        val = 0
        mask = 1
        index = None
        for i in range(8):
            if life & mask:
                if index is None:
                    val = payload[pos]
                    index = i
                    self.lis[index] = val & 0xF
                else:
                    self.lis[i] = val >> 4
                    print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + f"LIS{i+1} & LIS{index+1} (Loop In State)")
                    pos += 1
                    index = None
            mask = mask << 1
        if index:
            print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + f"LIS{index+1} (Loop In State)")
            pos += 1
        print()
        return pos

    def encoding(self):
        res = bytearray()
        life = 0
        for k in self.lis.keys():
            life |= 1 << k
        res += struct.pack('<B', life)
        val = None
        for v in self.lis.values():
            if val is None:
                val = v
            else:
                res += struct.pack('<B', v << 4 | val)
                val = None
        if val is not None:
            res += struct.pack('<B', val)
        return res


if __name__ == "__main__":
    origin = LoopinData(None)
    flg = random.randint(0, 0xFF)
    msk = 1
    for j in range(8):
        if flg & msk:
            offset = random.randint(-1, 3)
            value = 0 if offset == -1 else 1 << offset
            origin.lis[j] = value
        msk = msk << 1
    pl = origin.encoding()
    duplicate = LoopinData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
