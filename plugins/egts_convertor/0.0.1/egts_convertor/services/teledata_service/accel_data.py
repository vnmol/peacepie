import random
import struct
from datetime import datetime

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class AccelData(SubRecord):

    class AccelerometerDataStructure:

        def __init__(self):
            self.rtm = None
            self.xaav = None
            self.yaav = None
            self.zaav = None

        def __repr__(self):
            return f'(rtm={self.rtm!r}, xaav={self.xaav!r}, yaav={self.yaav!r}, zaav={self.zaav!r})'

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_ACCEL_DATA, srl)
        self.atm = None
        self.ads = []

    def decode(self, payload, pos):
        sa, self.atm = struct.unpack_from("<BI", payload, pos)
        pos += 5
        for _ in range(sa):
            ads = AccelData.AccelerometerDataStructure()
            ads.rtm, ads.xaav, ads.yaav, ads.zaav = struct.unpack_from("<Hhhh", payload, pos)
            self.ads.append(ads)
            pos += 8
        return pos

    def decode_with_print(self, payload, pos):
        sa, self.atm = struct.unpack_from("<BI", payload, pos)
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "SA (Structures Amount)")
        pos += 1
        value = f"{payload[pos]:02X} {payload[pos+1]:02X} {payload[pos+2]:02X} {payload[pos+3]:02X}".ljust(16)
        print(" " * 12 + value + "ATM (Absolute Time)")
        pos += 4
        for _ in range(sa):
            print()
            ads = AccelData.AccelerometerDataStructure()
            ads.rtm, ads.xaav, ads.yaav, ads.zaav = struct.unpack_from("<Hhhh", payload, pos)
            self.ads.append(ads)
            print(" " * 16 + f"{payload[pos]:02X} {payload[pos+1]:02X}".ljust(16) + "RTM (Relative Time)")
            pos += 2
            print(" " * 16 + f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "XAAV (X Axis Acceleration Value)")
            pos += 2
            print(" " * 16 + f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "YAAV (Y Axis Acceleration Value)")
            pos += 2
            print(" " * 16 + f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "ZAAV (Z Axis Acceleration Value)")
            pos += 2
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<BI", len(self.ads), self.atm)
        for ads in self.ads:
            res += struct.pack("<Hhhh", ads.rtm, ads.xaav, ads.yaav, ads.zaav)
        return res


if __name__ == "__main__":
    origin = AccelData(None)
    origin.atm = int (datetime.now().timestamp())
    for _ in range(random.randint(1, 8)):
        ads = AccelData.AccelerometerDataStructure()
        ads.rtm = random.randint(1, 0xFF)
        ads.xaav = random.randint(-32768, 32767)
        ads.yaav = random.randint(-32768, 32767)
        ads.zaav = random.randint(-32768, 32767)
        origin.ads.append(ads)
    pl = origin.encoding()
    duplicate = AccelData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate

