import enum
import struct
from calendar import prcal

from egts_convertor import constants
from egts_convertor.checksums import crc8_dallas


class TransportHeader:


    class State(enum.Enum):
        HEAD = enum.auto()
        BODY = enum.auto()
        READY = enum.auto()


    def __init__(self, parent):
        self.parent = parent
        self.state = self.State.HEAD
        self.prv = None
        self.skid = None
        self.prf = None
        self.rte = None
        self.ena = None
        self.cmp = None
        self.pr = None
        self.hl = None
        self.he = None
        self.fdl = None
        self.pid = None
        self.pt = None
        self.pra = None
        self.rca = None
        self.ttl = None
        self.hcs = None

    def set(self, pid, pt):
        self.prv = 1
        self.skid = 0
        self.prf = 0
        self.rte = 0
        self.ena = 0
        self.cmp = 0
        self.pr = 2
        if self.rte:
            self.hl = constants.ROUTE_HEADER_TRANSPORT_SIZE
        else:
            self.hl = constants.HEADER_TRANSPORT_SIZE
        self.he = 0
        self.pid = pid
        self.pt = pt

    def decode(self, data, pos):
        if self.state is self.state.HEAD:
            if len(data) < constants.PACKET_HEADER_FIRST_SIZE:
                return pos
            self.prv, self.skid, flags, self.hl = struct.unpack_from("<BBBB", data)
            self.prf = flags >> 6
            self.rte = (flags >> 5) & 0x01
            self.ena = (flags >> 3) & 0x03
            self.cmp = (flags >> 2) & 0x01
            self.pr = flags & 0x03
            if self.prv != constants.PACKET_HEADER_VERSION or self.prf != constants.PACKET_HEADER_PREFIX:
                raise ValueError(constants.EGTS_PC_UNS_PROTOCOL)
            if self.hl != constants.HEADER_TRANSPORT_SIZE and self.hl != constants.ROUTE_HEADER_TRANSPORT_SIZE:
                raise ValueError(constants.EGTS_PC_INC_HEADERFORM)
            pos += constants.PACKET_HEADER_FIRST_SIZE
            self.state = self.state.BODY
        if self.state is self.state.BODY:
            if len(data) < self.hl:
                return pos
            self.hcs = data[self.hl - 1]
            if self.hcs != crc8_dallas(data[:self.hl - 1]):
                raise ValueError(constants.EGTS_PC_HEADERCRC_ERROR)
            self.he, self.fdl, self.pid, self.pt = struct.unpack_from("<BHHB", data, pos)
            pos += constants.PACKET_HEADER_SECOND_SIZE
            self.parent.parent.pid = self.pid
            if self.rte:
                self.pra, self.rca, self.ttl = struct.unpack_from("<HHB", data, pos)
                pos += constants.PACKET_HEADER_THIRD_SIZE
            pos += 1 # для контрольной суммы
            self.state = self.State.READY
        return pos

    def decode_with_print(self, data, pos):
        packet_types = {
            constants.EGTS_PT_RESPONSE: "EGTS_PT_RESPONSE",
            constants.EGTS_PT_APPDATA: "EGTS_PT_APPDATA"
        }
        if self.state is self.state.HEAD:
            if len(data) < constants.PACKET_HEADER_FIRST_SIZE:
                return pos
            self.prv, self.skid, flags, self.hl = struct.unpack_from("<BBBB", data)
            print(f"{data[0]:02X}".ljust(16) + "PRV (Protocol Version)")
            print(f"{data[1]:02X}".ljust(16) + "SKID (Security Key ID)")
            self.prf = flags >> 6
            self.rte = (flags >> 5) & 0x01
            self.ena = (flags >> 3) & 0x03
            self.cmp = (flags >> 2) & 0x01
            self.pr = flags & 0x03
            value = (f"PRF(Prefix)={self.prf} RTE(Route)={self.rte} ENA(Encryption Algorithm)={self.ena} "
                     f"CMP(Compressed)={self.cmp} PR(Priority)={self.pr}")
            print(f"{data[2]:02X}".ljust(16) + value)
            print(f"{data[3]:02X}".ljust(16) + "HL (Header Length)")
            if self.prv != constants.PACKET_HEADER_VERSION or self.prf != constants.PACKET_HEADER_PREFIX:
                raise ValueError(constants.EGTS_PC_UNS_PROTOCOL)
            if self.hl != constants.HEADER_TRANSPORT_SIZE and self.hl != constants.ROUTE_HEADER_TRANSPORT_SIZE:
                raise ValueError(constants.EGTS_PC_INC_HEADERFORM)
            pos += constants.PACKET_HEADER_FIRST_SIZE
            self.state = self.state.BODY
        if self.state is self.state.BODY:
            if len(data) < self.hl:
                return pos
            self.hcs = data[self.hl - 1]
            if self.hcs != crc8_dallas(data[:self.hl - 1]):
                raise ValueError(constants.EGTS_PC_HEADERCRC_ERROR)
            self.he, self.fdl, self.pid, self.pt = struct.unpack_from("<BHHB", data, pos)
            pos += constants.PACKET_HEADER_SECOND_SIZE
            if self.parent.parent:
                self.parent.parent.pid = self.pid
            print(f"{data[4]:02X}".ljust(16) + "HE (Header Encoding)")
            print(f"{data[5]:02X} {data[6]:02X}".ljust(16) + "FDL (Frame Data Length)")
            print(f"{data[7]:02X} {data[8]:02X}".ljust(16) + "PID (Packet Identifier)")
            print(f"{data[9]:02X}".ljust(16) + f"PT(Packet Type)={packet_types.get(self.pt)}")
            pos = 10
            if self.rte:
                self.pra, self.rca, self.ttl = struct.unpack_from("<HHB", self.parent.data, self.parent.pos)
                pos += constants.PACKET_HEADER_THIRD_SIZE
                print(f"{data[10]:02X} {self.parent.data[11]:02X}".ljust(16) + "PRA (Peer Address)")
                print(f"{data[12]:02X} {self.parent.data[13]:02X}".ljust(16) + "RCA (Recipient Address)")
                print(f"{data[14]:02X}".ljust(16) + "TTL (Time To Live)")
                pos = 15
            print(f"{data[pos]:02X}".ljust(16) + "HCS (Header Check Sum)")
            print()
            pos += 1 # для контрольной суммы
            self.state = self.State.READY
        return pos

    def encode(self, fdl):
        self.fdl = fdl
        flags = self.pr
        flags |= self.cmp << 2
        flags |= self.ena << 3
        flags |= self.rte << 5
        flags |= self.prf << 6
        res = bytearray()
        res += struct.pack('<BBBBBHHB', self.prv, self.skid, flags, self.hl, self.he, self.fdl, self.pid, self.pt)
        if self.rte:
            res += struct.pack('<HHB', self.pra, self.rca, self.ttl)
        res.append(crc8_dallas(res))
        return res

    def build_response(self, packet, pid):
        packet.header.prv = self.prv
        packet.header.skid = self.skid
        packet.header.prf = self.prf
        packet.header.rte = self.rte
        packet.header.ena = self.ena
        packet.header.cmp = self.cmp
        packet.header.pr = self.pr
        if self.rte:
            packet.header.hl = constants.ROUTE_HEADER_TRANSPORT_SIZE
            packet.header.pra = self.rca
            packet.header.rca = self.pra
            packet.header.ttl = 30
        else:
            packet.header.hl = constants.HEADER_TRANSPORT_SIZE
        packet.header.he = self.he
        packet.header.pid = pid
        packet.header.pt = constants.EGTS_PT_RESPONSE
