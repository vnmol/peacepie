import random
import struct
import sys

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class LiquidLevelSensor(SubRecord):
    
    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_LIQUID_LEVEL_SENSOR, srl)
        self.llsef = None
        self.llsvu = None
        self.rdf = None
        self.llsn = None
        self.maddr = None
        self.llsd = None

    def decode(self, payload, pos):
        flags, self.maddr = struct.unpack_from("<BH", payload, pos)
        self.llsef = (flags >> 6) & 0b001
        self.llsvu = (flags >> 4) & 0b011
        self.rdf   = (flags >> 3) & 0b001
        self.llsn  = flags & 0b111
        pos += 3
        l = self.srl - 3 if self.rdf else 4
        self.llsd = int.from_bytes(payload[pos:pos + l], 'little')
        pos += l
        return pos

    def decode_with_print(self, payload, pos):
        flags, self.maddr = struct.unpack_from("<BH", payload, pos)
        self.llsef = (flags >> 6) & 0b001
        self.llsvu = (flags >> 4) & 0b011
        self.rdf   = (flags >> 3) & 0b001
        self.llsn  = flags & 0b111
        value = (f"LLSEF(Liquid Level Sensor Error Flag)={self.llsef}, "
                 f"LLSVU(Liquid Level Sensor Value Unit)={self.llsvu}, "
                 f"RDF(Raw Data Flag)={self.rdf}, "
                 f"LLSN(Liquid Level Sensor Number)={self.llsn}")
        print(" " * 12 + f'{payload[pos]:02X}'.ljust(16) + value)
        pos += 1
        print(" " * 12 + f'{payload[pos]:02X} {payload[pos+1]:02X}'.ljust(16) + 'MADDR (Module Address)')
        pos += 2
        l = self.srl - 3 if self.rdf else 4
        self.llsd = int.from_bytes(payload[pos:pos + l], 'little')
        value = f'{payload[pos]:02X}'
        for i in range(pos + 1, pos + l):
            value += f' {payload[i]:02X}'
        print(" " * 12 + value + '    LLSD (Liquid Level Sensor Data)')
        pos += l
        print()
        return pos

    def encoding(self):
        res = bytearray()
        flags = (
                ((self.llsef & 0b001) << 6) |
                ((self.llsvu & 0b011) << 4) |
                ((self.rdf   & 0b001) << 3) |
                 (self.llsn  & 0b111)
        )
        res += struct.pack("<BH", flags, self.maddr)
        l = (self.llsd.bit_length() + 7) // 8 or 1 if self.rdf else 4
        res += self.llsd.to_bytes(l, byteorder='little')
        return res

if __name__ == "__main__":
    origin = LiquidLevelSensor(None)
    origin.llsef = random.randint(0, 1)
    origin.llsvu = random.randint(0, 2)
    origin.rdf = random.randint(0, 1)
    origin.llsn = random.randint(0, 7)
    origin.maddr = random.randint(0, 0xFFFF)
    count = random.randint(0, 4)
    mask = 0xFFFFFFFF
    for i in range(count):
        mask = mask << 8 | 0xFF
    origin.llsd = random.randint(0, mask if origin.rdf else 0xFFFFFFFF)
    srl = 3 + ((origin.llsd.bit_length() + 7) // 8 or 1)
    origin.srl = srl
    pl = origin.encoding()
    duplicate = LiquidLevelSensor(None, srl)
    duplicate.decode(pl, 0)
    assert origin == duplicate
