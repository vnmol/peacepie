import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class ExtPosData(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_EXT_POS_DATA, srl)
        self.vdop = None
        self.hdop = None
        self.pdop = None
        self.sat = None
        self.ns = None

    def decode(self, payload, pos):
        flags, = struct.unpack_from("<B", payload, pos)
        pos += 1
        if flags & 0b00000001:
            self.vdop, = struct.unpack_from("<H", payload, pos)
            pos += 2
        if flags & 0b00000010:
            self.hdop, = struct.unpack_from("<H", payload, pos)
            pos += 2
        if flags & 0b00000100:
            self.pdop, = struct.unpack_from("<H", payload, pos)
            pos += 2
        if flags & 0b00001000:
            self.sat, self.ns = struct.unpack_from("<BH", payload, pos)
            pos += 3
        elif flags & 0b00010000:
            self.ns, = struct.unpack_from("<H", payload, pos)
            pos += 2
        return pos

    def decode_with_print(self, payload, pos):
        nav_systems = {0: 'UNKNOWN', 1: 'GLONASS', 2: 'GPS', 4: 'Galileo', 8: 'Compass',
                       16: 'Beidou', 32: 'DORIS', 64: 'IRNSS', 128: 'QZSS'}
        flags, = struct.unpack_from("<B", payload, pos)
        nsfe = (flags >> 4) & 0x01
        sfe = (flags >> 3) & 0x01
        pfe = (flags >> 2) & 0x01
        hfe = (flags >> 1) & 0x01
        vfe = flags & 0x01
        value = (f"NSFE(Navigation System Field Exists)={nsfe} SFE(Satellites Field Exists)={sfe} "
                 f"PFE(PDOP Field Exists)={pfe} HFE(HDOP Field Exists)={hfe} VFE(VDOP Field Exists)={vfe}")
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + value)
        pos += 1
        if flags & 0b00000001:
            self.vdop, = struct.unpack_from("<H", payload, pos)
            print(" " * 12 + f"{payload[pos]:02X} {payload[pos+1]:02X}".ljust(16) + "VDOP (Vertical Dilution of Precision)")
            pos += 2
        if flags & 0b00000010:
            self.hdop, = struct.unpack_from("<H", payload, pos)
            print(" " * 12 + f"{payload[pos]:02X} {payload[pos+1]:02X}".ljust(16) + "HDOP (Horizontal Dilution of Precision)")
            pos += 2
        if flags & 0b00000100:
            self.pdop, = struct.unpack_from("<H", payload, pos)
            print(" " * 12 + f"{payload[pos]:02X} {payload[pos+1]:02X}".ljust(16) + "PDOP (Position Dilution of Precision)")
            pos += 2
        if flags & 0b00001000:
            self.sat, self.ns = struct.unpack_from("<BH", payload, pos)
            if not nav_systems.get(self.ns):
                self.ns = 0
            print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "SAT (Satellites)")
            print(" " * 12 + f"{payload[pos+1]:02X} {payload[pos+2]:02X}".ljust(16) + f"NS(Navigation System)={nav_systems.get(self.ns)}")
            pos += 3
        elif flags & 0b00010000:
            self.ns, = struct.unpack_from("<H", payload, pos)
            if not nav_systems.get(self.ns):
                self.ns = 0
            print(" " * 12 + f"{payload[pos]:02X} {payload[pos+1]:02X}".ljust(16) + f"NS(Navigation System)={nav_systems.get(self.ns)}")
            pos += 2
        print()
        return pos

    def encoding(self):
        flags = 0
        res = bytearray()
        if self.vdop is not None:
            flags |= 0b00000001
        if self.hdop is not None:
            flags |= 0b00000010
        if self.pdop is not None:
            flags |= 0b00000100
        if self.sat is not None and self.ns is not None:
            flags |= 0b00001000
        elif self.ns is not None:
            flags |= 0b00010000
        res += struct.pack("<B", flags)
        if flags & 0b00000001:
            res += struct.pack("<H", self.vdop)
        if flags & 0b00000010:
            res += struct.pack("<H", self.hdop)
        if flags & 0b00000100:
            res += struct.pack("<H", self.pdop)
        if flags & 0b00001000:
            res += struct.pack("<BH", self.sat, self.ns)
        elif flags & 0b00010000:
            res += struct.pack("<H", self.ns)
        return res


if __name__ == "__main__":
    origin = ExtPosData(None)
    duplicate = ExtPosData(None)
    for flgs in range(0x1F):
        origin.clear()
        if flgs & 0b00000001:
            origin.vdop = random.randint(0, 0xFFFF)
        if flgs & 0b00000010:
            origin.hdop = random.randint(0, 0xFFFF)
        if flgs & 0b00000100:
            origin.pdop = random.randint(0, 0xFFFF)
        if flgs & 0b00001000:
            origin.sat = random.randint(0, 0xFF)
            n = random.randint(-1, 7)
            origin.ns = 0 if n == -1 else 1 << n
        elif flgs & 0b00010000:
            n = random.randint(-1, 7)
            origin.ns = 0 if n == -1 else 1 << n
        pl = origin.encoding()
        duplicate.clear()
        duplicate.decode(pl, 0)
        assert origin == duplicate
