import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class PassengersCounters(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_PASSENGERS_COUNTERS, srl)
        self.rdf = None
        self.drl = None
        self.maddr = None
        self.pcd = {}

    def decode(self, payload, pos):
        self.rdf, dpr, self.drl, self.maddr = struct.unpack_from("<BBBH", payload, pos)
        pos += 5
        if not self.rdf:
            dpr = (1 << ((self.parent.header.srl - 5) // 2)) - 1
        for i in range(8):
            if dpr & (0x01 << i):
                self.pcd[i] = {'IPQ': payload[pos], 'OPQ': payload[pos + 1]}
                pos += 2
        return pos

    def decode_with_print(self, payload, pos):
        self.rdf, dpr, self.drl, self.maddr = struct.unpack_from("<BBBH", payload, pos)
        print(" " * 12 + f'{payload[pos]:02X}'.ljust(16) + 'RDF (Raw Data Flag)')
        pos += 1
        print(" " * 12 + f'{payload[pos]:02X}'.ljust(16) + 'DPR (Doors Presented)')
        pos += 1
        print(" " * 12 + f'{payload[pos]:02X}'.ljust(16) + 'DRL (Doors Released)')
        pos += 1
        print(" " * 12 + f'{payload[pos]:02X} {payload[pos+1]:02X}'.ljust(16) + 'MADDR (Module Address)')
        pos += 2
        print()
        if not self.rdf:
            dpr = (1 << ((self.parent.header.srl - 5) // 2)) - 1
        for i in range(8):
            if dpr & (0x01 << i):
                self.pcd[i] = {'IPQ': payload[pos], 'OPQ': payload[pos + 1]}
                print(" " * 16 + f'{payload[pos]:02X}'.ljust(16) + f'IPQ{i+1} (In Passengers Quantity {i+1})')
                pos += 1
                print(" " * 16 + f'{payload[pos]:02X}'.ljust(16) + f'OPQ{i+1} (Out Passengers Quantity {i+1})')
                pos += 1
                print()
        return pos

    def encoding(self):
        res = bytearray()
        dpr = 0
        for i in range(8):
            if self.pcd.get(i):
                dpr |= (0x01 << i)
        res += struct.pack("<BBBH", self.rdf, dpr, self.drl, self.maddr)
        for i in range(8):
            pcd = self.pcd.get(i)
            if pcd:
                res.append(pcd.get('IPQ'))
                res.append(pcd.get('OPQ'))
        return res


if __name__ == "__main__":
    origin = PassengersCounters(None)
    origin.rdf = 1
    origin.drl = random.randint(0, 0xFF)
    origin.maddr = random.randint(0, 0xFFFF)
    dpr = random.randint(0, 0xFF)
    for i in range(8):
        if dpr & (0x01 << i):
            origin.pcd[i] = {'IPQ': random.randint(0, 0xFF), 'OPQ': random.randint(0, 0xFF)}
    pl = origin.encoding()
    duplicate = PassengersCounters(None)
    duplicate.decode(pl, 0)
    duplicate.parent = None
    assert origin == duplicate
