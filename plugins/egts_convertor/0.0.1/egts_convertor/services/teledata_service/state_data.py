import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class StateData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_STATE_DATA, srl)
        self.st = None
        self.mpsv = None
        self.bbv = None
        self.ibv = None
        self.flg = None

    def decode(self, payload, pos):
        self.st, self.mpsv, self.bbv, self.ibv, self.flg = struct.unpack_from("<BBBBB", payload, pos)
        pos += 5
        return pos

    def decode_with_print(self, payload, pos):
        self.st, self.mpsv, self.bbv, self.ibv, self.flg = struct.unpack_from("<BBBBB", payload, pos)
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "ST (State )")
        pos += 1
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "MPSV (Main Power Source Voltage)")
        pos += 1
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "BBV (Back Up Battery Voltage)")
        pos += 1
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "IBV  (Internal Battery Voltage)")
        pos += 1
        value = f'NMS={(self.flg >> 2) & 0x01}, IBU={(self.flg >> 1) & 0x01}, BBU={self.flg & 0x01}'
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + value)
        pos += 1
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<BBBBB", self.st, self.mpsv, self.bbv, self.ibv, self.flg)
        return res


if __name__ == "__main__":
    origin = StateData(None)
    origin.st = random.randint(1, 7)
    origin.mpsv = random.randint(0, 255)
    origin.bbv = random.randint(0, 255)
    origin.ibv = random.randint(0, 255)
    origin.flg = random.randint(1, 7)
    pl = origin.encoding()
    duplicate = StateData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
