import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class AdSensorsData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_AD_SENSORS_DATA, srl)
        self.dout = None
        self.adio = {}
        self.ans = {}

    def decode(self, payload, pos):
        dioe, self.dout, asfe = struct.unpack_from("<BBB", payload, pos)
        pos += 3
        for i in range(8):
            if dioe & 0x01:
                self.adio[i] = payload[pos]
                pos += 1
            dioe = dioe >> 1
        for i in range(8):
            if asfe & 0x01:
                self.ans[i] = int.from_bytes(payload[pos:pos + 3], 'little')
                pos += 3
            asfe = asfe >> 1
        return pos

    def decode_with_print(self, payload, pos):
        dioe, self.dout, asfe = struct.unpack_from("<BBB", payload, pos)
        value = "DIOE (Digital Inputs Octet Exists) {"
        dioe_for_print = dioe
        for i in range(8):
            if dioe_for_print & 0x01:
                value += f' DIOE{i+1}'
            dioe_for_print = dioe_for_print >> 1
        value += " }"
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + value)
        print(" " * 12 + f"{payload[pos+1]:02X}".ljust(16) + "DOUT (Digital Outputs)")
        value = "ASFE (Analog Sensor Field Exists) {"
        asfe_for_print = asfe
        for i in range(8):
            if asfe_for_print & 0x01:
                value += f' ASFE{i+1}'
            asfe_for_print = asfe_for_print >> 1
        value += " }"
        print(" " * 12 + f"{payload[pos+2]:02X}".ljust(16) + value)
        pos += 3
        for i in range(8):
            if dioe & 0x01:
                self.adio[i] = payload[pos]
                print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + f"ADIO{i+1} (Additional Digital Inputs Octet {i+1})")
                pos += 1
            dioe = dioe >> 1
        for i in range(8):
            if asfe & 0x01:
                self.ans[i] = int.from_bytes(payload[pos:pos + 3], 'little')
                value = f"{payload[pos]:02X} {payload[pos+1]:02X} {payload[pos+2]:02X}".ljust(16)
                print(" " * 12 + value + f"ANS{i+1} (Analog Sensor {i+1})")
                pos += 3
            asfe = asfe >> 1
        print()
        return pos

    def encoding(self):
        if self.dout is None:
            self.dout = 0
        res = bytearray()
        dioe = 0
        for key in self.adio.keys():
            dioe |= 1 << key
        asfe = 0
        for key in self.ans.keys():
            asfe |= 1 << key
        res += struct.pack("<BBB", dioe, self.dout, asfe)
        for value in self.adio.values():
            res += struct.pack("<B", value)
        for value in self.ans.values():
            res += value.to_bytes(3, 'little')
        return res


if __name__ == "__main__":
    origin = AdSensorsData(None)
    duplicate = AdSensorsData(None)
    for flag in range(0x100):
        origin.clear()
        origin.dout = random.getrandbits(8)
        for i in range(8):
            if flag & (0x01 << i):
                origin.adio[i] = random.getrandbits(8)
        for i in range(8):
            if flag & (0x01 << i):
                origin.ans[i] = random.getrandbits(24)
        pl = origin.encoding()
        duplicate.clear()
        duplicate.decode(pl, 0)
        assert origin == duplicate
