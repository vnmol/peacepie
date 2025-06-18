import random
import struct
from datetime import datetime, timezone

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class PosData(SubRecord):

    ALTE = 0b10000000
    LOHS = 0b01000000
    LAHS = 0b00100000
    MV   = 0b00010000
    BB   = 0b00001000
    CS   = 0b00000100
    FIX  = 0b00000010
    VLD  = 0b00000001

    DIRH = 0b1000000000000000
    ALTS = 0b0100000000000000

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_POS_DATA, srl)
        self.ntm = None
        self.lat = None
        self.long = None
        self.flag = None
        self.spd = 0
        self.dir = 0
        self.odm = 0
        self.din = 0
        self.src = 0
        self.alt = None

    def get_datetime(self):
        return datetime.fromtimestamp(self.ntm + constants.DEFAULT_BEGIN_TIME, tz=timezone.utc).isoformat()

    def set_datetime(self, val):
        self.ntm = int(datetime.fromisoformat(val).timestamp()) - constants.DEFAULT_BEGIN_TIME

    def get_lat(self):
        return self.lat * 90 / 0xFFFFFFFF * (-1 if self.flag & PosData.LAHS else 1)

    def set_lat(self, val):
        self.set_flag_bit(PosData.LAHS, val < 0)
        self.lat = int(abs(val) / 90 * 0xFFFFFFFF)

    def get_long(self):
        return self.long * 180 / 0xFFFFFFFF * (-1 if self.flag & PosData.LOHS else 1)

    def set_long(self, val):
        self.set_flag_bit(PosData.LOHS, val < 0)
        self.long = int(abs(val) / 180 * 0xFFFFFFFF)

    def get_mv(self):
        return 1 if self.flag & PosData.MV else 0

    def set_mv(self, val):
        self.set_flag_bit(PosData.MV, val)

    def get_bb(self):
        return 1 if self.flag & PosData.BB else 0

    def set_bb(self, val):
        self.set_flag_bit(PosData.BB, val)

    def get_fix(self):
        return 1 if self.flag & PosData.FIX else 0

    def set_fix(self, val):
        self.set_flag_bit(PosData.FIX, val)

    def get_cs(self):
        return 1 if self.flag & PosData.CS else 0

    def set_cs(self, val):
        self.set_flag_bit(PosData.CS, val)

    def get_vld(self):
        return 1 if self.flag & PosData.VLD else 0

    def set_vld(self, val):
        self.set_flag_bit(PosData.VLD, val)

    def get_spd(self):
        return (self.spd & 0x3FFF) * 0.1852

    def set_spd(self, val):
        if val is None:
            val = 0.0
        if self.spd is None:
            self.spd = 0
        self.spd = (self.spd & (PosData.DIRH | PosData.ALTS)) | (round(val / 0.1852) & 0x3FFF)

    def get_dir(self):
        return ((self.spd & PosData.DIRH) >> 7) | self.dir

    def set_dir(self, val):
        if val is None:
            val = 0
        self.set_spd_bit(PosData.DIRH, val > 0xFF)
        self.dir = val & 0xFF

    def get_odm(self):
        return self.odm / 10

    def set_odm(self, val):
        if val is None:
            val = 0.0
        self.odm = int(val * 10)

    def get_din(self):
        return self.din

    def set_din(self, val):
        if val is None:
            val = 0
        self.din = val

    def get_src(self):
        return self.src

    def set_src(self, val):
        if val is None:
            val = 0
        self.src = val

    def get_alt(self):
        return self.alt / 1000 * (-1 if self.spd & PosData.ALTS else 1)

    def set_alt(self, val):
        self.set_flag_bit(PosData.ALTE, True)
        self.set_spd_bit(PosData.ALTS, val < 0)
        self.alt = int(abs(val) * 1000) & 0xFFFFFF

    def set_flag_bit(self, mask, set_flag):
        if self.flag is None:
            self.flag = 0
        if set_flag:
            self.flag |= mask
        else:
            self.flag &= mask ^ 0xFF

    def set_spd_bit(self, mask, set_flag):
        if self.spd is None:
            self.spd = 0
        if set_flag:
            self.spd |= mask
        else:
            self.spd &= mask ^ 0xFFFF

    def decode(self, payload, pos):
        self.ntm, self.lat, self.long, self.flag, self.spd, self.dir = struct.unpack_from("<IIIBHB", payload, pos)
        pos += 16
        self.odm = int.from_bytes(payload[pos:pos + 3], 'little')
        pos += 3
        self.din, self.src = struct.unpack_from("<BB", payload, pos)
        pos += 2
        if self.flag & PosData.ALTE:
            self.alt = int.from_bytes(payload[pos:pos + 3], 'little')
            pos += 3
        return pos

    def decode_with_print(self, payload, pos):
        self.ntm, self.lat, self.long, self.flag, self.spd, self.dir = struct.unpack_from("<IIIBHB", payload, pos)
        alte = (self.flag >> 7) & 0x01
        lohs = (self.flag >> 6) & 0x01
        lahs = (self.flag >> 5) & 0x01
        mv = (self.flag >> 4) & 0x01
        bb = (self.flag >> 3) & 0x01
        cs = (self.flag >> 2) & 0x01
        fix = (self.flag >> 1) & 0x01
        vld = self.flag & 0x01
        buf = payload[pos:pos + 4]
        value = " ".join([format(byte, "02X") for byte in buf]).ljust(16)
        print(" " * 12 + value + "NTM (Navigation Time)")
        pos += 4
        buf = payload[pos:pos + 4]
        value = " ".join([format(byte, "02X") for byte in buf]).ljust(16)
        print(" " * 12 + value + "LAT (Latitude)")
        pos += 4
        buf = payload[pos:pos + 4]
        value = " ".join([format(byte, "02X") for byte in buf]).ljust(16)
        print(" " * 12 + value + "LONG (Longitude)")
        pos += 4
        value = f"(ALTE={alte} LOHS={lohs} LAHS={lahs} MV={mv} BB={bb} CS={cs} FIX={fix} VLD={vld})"
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + f"FLG(Flags)={value}")
        pos += 1
        value = (f"SPD (Speed) (DIRH(Direction the Highest bit)={(self.spd >> 15) & 0x01} "
                 f"ALTS(Altitude Sign)={(self.spd >> 14) & 0x01})")
        print(" " * 12 + f"{payload[pos]:02X} {payload[pos+1]:02X}".ljust(16) + f"{value}")
        pos += 2
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "DIR (Direction)")
        pos += 1
        self.odm = int.from_bytes(payload[pos:pos + 3], 'little')
        print(" " * 12 + f"{payload[pos]:02X} {payload[pos+1]:02X} {payload[pos+2]:02X}".ljust(16) + "ODM (Odometer)")
        pos += 3
        self.din, self.src = struct.unpack_from("<BB", payload, pos)
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "DIN (Digital Inputs)")
        pos += 1
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + "SRC (Source)")
        pos += 1
        if alte:
            self.alt = int.from_bytes(payload[pos:pos + 3], 'little')
            value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X}".ljust(16)
            print(" " * 12 + value + "ALT (Altitude)")
            pos += 3
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<IIIBHB", self.ntm, self.lat, self.long, self.flag, self.spd, self.dir)
        res += self.odm.to_bytes(3, 'little')
        res += struct.pack("<BB", self.din, self.src)
        if self.alt is not None:
            res += self.alt.to_bytes(3, 'little')
        return res


if __name__ == "__main__":
    origin = PosData(None)
    origin.set_datetime(datetime.now())
    origin.set_lat(random.uniform(-90, 90))
    origin.set_long(random.uniform(-180, 180))
    origin.set_mv(random.randint(0, 1))
    origin.set_bb(random.randint(0, 1))
    origin.set_fix(random.randint(0, 1))
    origin.set_cs(random.randint(0, 1))
    origin.set_vld(random.randint(0, 1))
    origin.set_spd(random.uniform(0, 100))
    origin.set_dir(random.randint(0, 359))
    origin.set_odm(random.uniform(0, 1000))
    origin.set_din(random.randint(0, 0xFF))
    origin.set_src(random.randint(0, 35))
    origin.set_alt(random.uniform(-100, 100))
    pl = origin.encoding()
    duplicate = PosData(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
