from _datetime import datetime, timezone
import struct

from egts_convertor import constants, utils


class RecordHeader:

    def __init__(self, parent):
        self.parent = parent
        self.rl = None
        self.rn = None
        self.ssod = None
        self.rsod = None
        self.grp = None
        self.rpp = None
        self.oid = None
        self.evid = None
        self.tm = None
        self.sst = None
        self.rst = None

    def set(self, rn, ssod, rsod, sst, rst):
        self.rn = rn
        self.ssod = ssod
        self.rsod = rsod
        self.grp = 0
        self.rpp = 2
        self.oid = 0
        self.evid = 0
        self.tm = utils.get_now()
        self.sst = sst
        self.rst = rst

    def decode(self, payload, pos):
        self.rl, self.rn, rfl = struct.unpack_from("<HHB", payload, pos)
        pos += 5
        self.ssod = (rfl >> 7) & 0x01
        self.rsod = (rfl >> 6) & 0x01
        self.grp = (rfl >> 5) & 0x01
        self.rpp = (rfl >> 3) & 0x03
        if rfl & 0b00000001:
            self.oid, = struct.unpack_from("<I", payload, pos)
            pos += 4
        if rfl & 0b00000010:
            self.evid, = struct.unpack_from("<I", payload, pos)
            pos += 4
        if rfl & 0b00000100:
            self.tm, = struct.unpack_from("<I", payload, pos)
            pos += 4
        self.sst, self.rst = struct.unpack_from("<BB", payload, pos)
        pos += 2
        return pos

    def decode_with_print(self, payload, pos):
        self.rl, self.rn, rfl = struct.unpack_from("<HHB", payload, pos)
        print(" " * 4 + f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "RL (Record Length)")
        print(" " * 4 + f"{payload[pos + 2]:02X} {payload[pos + 3]:02X}".ljust(16) + "RN (Record Number)")
        self.ssod = (rfl >> 7) & 0x01
        self.rsod = (rfl >> 6) & 0x01
        self.grp = (rfl >> 5) & 0x01
        self.rpp = (rfl >> 3) & 0x03
        tmfe = (rfl >> 2) & 0x01
        evfe = (rfl >> 1) & 0x01
        obfe = rfl & 0x01
        value = (f"(SSOD(Source Service On Device)={self.ssod} RSOD(Recipient Service On Device)={self.rsod} "
                 f"GRP(Group)={self.grp} RPP(Record Processing Priority)={self.rpp} TMFE(Time Field Exists)={tmfe} "
                 f"EVFE(Event ID Field  Exists)={evfe} OBFE(Object ID Field Exists)={obfe})")
        print(" " * 4 + f"{payload[pos + 4]:02X}".ljust(16) + f"RFL(Record Flags)={value}")
        pos += 5
        if rfl & 0b00000001:
            self.oid, = struct.unpack_from("<I", payload, pos)
            value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X} {payload[pos + 3]:02X}".ljust(16)
            print(" " * 4 + value + "OID (Object Identifier)")
            pos += 4
        if rfl & 0b00000010:
            self.evid, = struct.unpack_from("<I", payload, pos)
            value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X} {payload[pos + 3]:02X}".ljust(16)
            print(" " * 4 + value + "EVID (Event Identifier)")
            pos += 4
        if rfl & 0b00000100:
            self.tm, = struct.unpack_from("<I", payload, pos)
            value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X} {payload[pos + 3]:02X}".ljust(16)
            print(" " * 4 + value + "TM (Time)")
            pos += 4
        self.sst, self.rst = struct.unpack_from("<BB", payload, pos)
        print(" " * 4 + f"{payload[pos]:02X}".ljust(16) +
              f"SST (Source Service Type)={constants.service_types.get(self.sst)}")
        print(" " * 4 + f"{payload[pos + 1]:02X}".ljust(16) +
              f"RST (Recipient Service Type)={constants.service_types.get(self.rst)}")
        print()
        pos += 2
        return pos

    def encode(self, rl):
        self.rl = rl
        res = bytearray()
        rfl = (self.ssod & 0x01) << 7
        rfl |= (self.rsod & 0x01) << 6
        rfl |= (self.grp & 0x01) << 5
        rfl |= (self.rpp & 0b11) << 3
        if self.tm is not None:
            rfl |= 0x01 << 2
        if self.evid is not None:
            rfl |= 0x01 << 1
        if self.oid is not None:
            rfl |= 0x01
        res += struct.pack("<HHB", self.rl, self.rn, rfl)
        if self.oid is not None:
            res += struct.pack("<I", self.oid)
        if self.evid is not None:
            res += struct.pack("<I", self.evid)
        if self.tm is not None:
            res += struct.pack("<I", self.tm)
        res += struct.pack("<BB", self.sst, self.rst)
        return res

    def build_response(self, header):
        header.rn = self.rn
        header.ssod = self.rsod
        header.rsod = self.ssod
        header.grp = self.grp
        header.rpp = self.rpp
        if self.oid is not None:
            header.oid = self.oid
        if self.evid is not None:
            header.evid = self.evid
        if self.tm is not None:
            header.tm = utils.get_now()
        header.sst = self.rst
        header.rst = self.sst
