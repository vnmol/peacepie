import random
import struct

from egts_convertor import constants
from egts_convertor.services.auth_service.result_code import ResultCode
from egts_convertor.services.sub_record import SubRecord


class TermIdentity(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_TERM_IDENTITY, srl)
        self.tid = None
        self.ssra = None
        self.hdid = None
        self.imei = None
        self.imsi = None
        self.lngc = None
        self.mcc = None
        self.mnc = None
        self.bs = None
        self.msisdn =None

    def set_imei(self, imei):
        self.tid = 0
        self.imei = imei

    def decode(self, payload, pos):
        self.tid, flags = struct.unpack_from("<IB", payload, pos)
        pos += 5
        self.ssra = (flags >> 4) & 0x01
        if flags & 0b00000001:
            self.hdid, = struct.unpack_from("<H", payload, pos)
            pos += 2
        if flags & 0b00000010:
            self.imei = payload[pos:pos+15].decode(constants.DEFAULT_CHARSET)
            pos += 15
        if flags & 0b00000100:
            self.imsi = payload[pos:pos+16].decode(constants.DEFAULT_CHARSET)
            pos += 16
        if flags & 0b00001000:
            self.lngc = payload[pos:pos+3].decode(constants.DEFAULT_CHARSET)
            pos += 3
        if flags & 0b00100000:
            nid = int.from_bytes(payload[pos:pos+3], 'little')
            pos += 3
            self.mcc = (nid >> 10) & 0x3FF
            self.mnc = nid & 0x3FF
        if flags & 0b01000000:
            self.bs, = struct.unpack_from("<H", payload, pos)
            pos += 2
        if flags & 0b10000000:
            self.msisdn = payload[pos:pos+15].decode(constants.DEFAULT_CHARSET)
            pos += 15
        return pos

    def decode_with_print(self, payload, pos):
        self.tid, flags = struct.unpack_from("<IB", payload, pos)
        value = f"{payload[pos]:02X} {payload[pos + 1]:02X} {payload[pos + 2]:02X} {payload[pos + 3]:02X}".ljust(16)
        print(" " * 12 + value + "TID (Terminal Identifier)")
        mne = (flags >> 7) & 0x01
        bse = (flags >> 6) & 0x01
        nide = (flags >> 5) & 0x01
        self.ssra = (flags >> 4) & 0x01
        lngce = (flags >> 3) & 0x01
        imsie = (flags >> 2) & 0x01
        imeie = (flags >> 1) & 0x01
        hdide = flags & 0x01
        value = (f"(MNE(Mobile Network Exists)={mne} BSE(Buffer Size Exists)={bse} "
                 f"NIDE(Network Identifier Exists)={nide} SSRA={self.ssra} LNGCE(Language Code Exists)={lngce} "
                 f"IMSIE(International Mobile Subscriber Identity Exists)={imsie} "
                 f"IMEIE(International Mobile Equipment Identity Exists)={imeie} "
                 f"HDIDE(Home Dispatcher Identifier Exists)={hdide}")
        print(" " * 12 + f"{payload[pos + 4]:02X}".ljust(16) + f"Flags={value})")
        pos += 5
        if flags & 0b00000001:
            self.hdid, = struct.unpack_from("<H", payload, pos)
            print(" " * 12 +  f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "HDID (Home Dispatcher Identifier)")
            pos += 2
        if flags & 0b00000010:
            buf = payload[pos:pos+15]
            self.imei = buf.decode(constants.DEFAULT_CHARSET)
            value = " ".join([format(byte, "02X") for byte in buf])
            print(" " * 12 +  value + f"   IMEI (International Mobile Equipment Identity)={self.imei}")
            pos += 15
        if flags & 0b00000100:
            buf = payload[pos:pos+16]
            self.imsi = buf.decode(constants.DEFAULT_CHARSET)
            value = " ".join([format(byte, "02X") for byte in buf])
            print(" " * 12 +  value + f"   IMSI (International Mobile Subscriber Identity)={self.imsi}")
            pos += 16
        if flags & 0b00001000:
            buf = payload[pos:pos+3]
            self.lngc = buf.decode(constants.DEFAULT_CHARSET)
            value = " ".join([format(byte, "02X") for byte in buf])
            print(" " * 12 +  value.ljust(16) + f"LNGC (Language Code)={self.lngc}")
            pos += 3
        if flags & 0b00100000:
            buf = payload[pos:pos+3]
            nid = int.from_bytes(buf, 'little')
            self.mcc = (nid >> 10) & 0x3FF
            self.mnc = nid & 0x3FF
            value = " ".join([format(byte, "02X") for byte in buf]).ljust(16)
            value += (f"NID (Network Identifier)="
                      f"(MCC(Mobile Country Code)={self.mcc} "
                      f"MNC(Mobile Network Code)={self.mnc})")
            print(" " * 12 +  value)
            pos += 3
        if flags & 0b01000000:
            self.bs, = struct.unpack_from("<H", payload, pos)
            print(" " * 12 +  f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "BS (Buffer Size)")
            pos += 2
        if flags & 0b10000000:
            buf = payload[pos:pos+15]
            self.msisdn = buf.decode(constants.DEFAULT_CHARSET)
            value = " ".join([format(byte, "02X") for byte in buf])
            print(" " * 12 +  value + f"   MSISDN(Mobile Station Integrated Services Digital Network Number)={self.msisdn}")
            pos += 15
        print()
        return pos

    def encoding(self):
        if self.ssra is None:
            self.ssra = 0
        flags = self.ssra << 4
        if self.hdid is not None:
            flags |= 0b00000001
        if self.imei is not None:
            flags |= 0b00000010
        if self.imsi is not None:
            flags |= 0b00000100
        if self.lngc is not None:
            flags |= 0b00001000
        if self.mcc is not None and self.mnc is not None:
            flags |= 0b00100000
        if self.bs is not None:
            flags |= 0b01000000
        if self.msisdn is not None:
            flags |= 0b10000000
        res = bytearray()
        res += struct.pack("<IB", self.tid, flags)
        if self.hdid is not None:
            res += struct.pack("<H", self.hdid)
        if self.imei is not None:
            res += self.imei.encode(constants.DEFAULT_CHARSET)
        if self.imsi is not None:
            res += self.imsi.encode(constants.DEFAULT_CHARSET)
        if self.lngc is not None:
            res += self.lngc.encode(constants.DEFAULT_CHARSET)
        if self.mcc is not None and self.mnc is not None:
            nid = (self.mcc << 10) | self.mnc
            res += nid.to_bytes(3, 'little')
        if self.bs is not None:
            res += struct.pack("<H", self.bs)
        if self.msisdn is not None:
            res += self.msisdn.encode(constants.DEFAULT_CHARSET)
        return res

    def build_response(self, record):
        sub_record = ResultCode(record, 0)
        sub_record.rcd = constants.EGTS_PC_OK
        record.sub_records.append(sub_record)


if __name__ == "__main__":
    hex_chars = '0123456789ABCDEF'
    origin = TermIdentity(None)
    duplicate = TermIdentity(None)
    for flags in range(0x100):
        origin.clear()
        origin.tid = random.randint(0, 0xFFFFFFFF)
        if flags & 0b00000001:
            origin.hdid = random.randint(0, 0xFFFF)
        if flags & 0b00000010:
            origin.imei = ''.join(random.choices(hex_chars, k=15))
        if flags & 0b00000100:
            origin.imsi = ''.join(random.choices(hex_chars, k=16))
        if flags & 0b00001000:
            origin.lngc = ''.join(random.choices(hex_chars, k=3))
        if flags & 0b00010000:
            origin.ssra = random.randint(0, 1)
        if flags & 0b00100000:
            origin.mcc = random.randint(0, 0x3FF)
            origin.mnc = random.randint(0, 0x3FF)
        if flags & 0b01000000:
            origin.bs = random.randint(0, 0xFFFF)
        if flags & 0b10000000:
            origin.msisdn = ''.join(random.choices(hex_chars, k=15))
        pl = origin.encoding()
        duplicate.clear()
        duplicate.decode(pl, 0)
        assert origin == duplicate
