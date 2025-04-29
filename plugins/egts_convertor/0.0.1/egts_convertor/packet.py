import enum
import logging
import struct

from egts_convertor import constants
from egts_convertor.checksums import crc16_ccitt
from egts_convertor.common_record import CommonRecord
from egts_convertor.response_record import ResponseRecord
from egts_convertor.transport_header import TransportHeader


class Packet:


    class State(enum.Enum):
        HEADER = enum.auto()
        BODY = enum.auto()
        READY = enum.auto()


    def __init__(self, parent):
        self.parent = parent
        self.state = self.State.HEADER
        self.header = TransportHeader(self)
        self.records = []
        self.payload = None

    def __repr__(self):
        return f'{constants.packet_types.get(self.header.pt)}({self.header.pid})({self.records})'

    def is_ready(self):
        return self.state == self.State.READY

    def decode(self, data, pos):
        if self.state is self.State.HEADER:
            pos = self.header.decode(data, pos)
            if self.header.state != TransportHeader.State.READY:
                return pos
            if self.header.fdl == 0:
                self.state = self.State.READY
                return pos
            else:
                self.state = self.State.BODY
        if self.state is self.State.BODY:
            if len(data) < self.header.fdl:
                return pos
            sfrcs, = struct.unpack_from("<H", data, pos + self.header.fdl)
            self.payload = data[pos : pos + self.header.fdl]
            if sfrcs != crc16_ccitt(self.payload):
                raise ValueError(constants.EGTS_PC_DATACRC_ERROR)
            pos += self.header.fdl
            pos += 2 # для контрольной суммы
        if self.header.rte and self.header.rca != self.parent.current_address:
            logging.info("Need to route a package")
            print("sendResponse(EGTSConstants.EGTS_PC_TTLEXPIRED)")
        elif self.normalize():
            self.records_decode(self.payload, 0)
            self.state = self.State.READY
        return pos

    def decode_with_print(self, data, pos):
        if self.state is self.State.HEADER:
            pos = self.header.decode_with_print(data, pos)
            if self.header.state != TransportHeader.State.READY:
                return pos
            if self.header.fdl == 0:
                self.state = self.State.READY
                return pos
            else:
                self.state = self.State.BODY
        if self.state is self.State.BODY:
            if len(data) < self.header.fdl:
                return pos
            sfrcs, = struct.unpack_from("<H", data, pos + self.header.fdl)
            self.payload = data[pos : pos + self.header.fdl]
            if sfrcs != crc16_ccitt(self.payload):
                raise ValueError(constants.EGTS_PC_DATACRC_ERROR)
            pos += self.header.fdl
            pos += 2 # для контрольной суммы
        if self.header.rte and self.header.rca != self.parent.current_address:
            logging.info("Need to route a package")
            print("sendResponse(EGTSConstants.EGTS_PC_TTLEXPIRED)")
        elif self.normalize():
            self.records_decode_with_print(self.payload, 0)
            value = "SFRCS (Services Frame Data Check Sum)"
            print(f"{data[pos-2]:02X} {data[pos-1]:02X}".ljust(16) + value)
            print()
            self.state = self.State.READY
        return pos

    def normalize(self):
        if not self.payload:
            return True
        if self.header.ena and not self.decrypt():
            return False
        if self.header.cmp and not self.uncompress():
            return False
        return True

    def decrypt(self):
        logging.info("Need to decrypt the data")
        print("sendResponse(EGTSConstants.EGTS_PC_DECRYPT_ERROR)")
        return False

    def uncompress(self):
        logging.info("Need to uncompress the data")
        print("sendResponse(EGTSConstants.EGTS_PC_INC_DATAFORM)")
        return False

    def records_decode(self, payload, pos):
        if self.header.pt == constants.EGTS_PT_RESPONSE:
            record = ResponseRecord(self)
            pos = record.decode(payload, pos)
            self.records.append(record)
        while pos < len(payload):
            record = CommonRecord(self)
            pos = record.decode(payload, pos)
            self.records.append(record)

    def records_decode_with_print(self, payload, pos):
        if self.header.pt == constants.EGTS_PT_RESPONSE:
            record = ResponseRecord(self)
            pos = record.decode_with_print(payload, pos)
            self.records.append(record)
        while pos < len(payload):
            record = CommonRecord(self)
            pos = record.decode_with_print(payload, pos)
            self.records.append(record)

    def encode(self):
        res = bytearray()
        records = self.records_encode()
        fdl = len(records)
        res += self.header.encode(fdl)
        if fdl:
            res += records
            sfrcs = crc16_ccitt(records)
            res += struct.pack('<H', sfrcs)
        return res

    def records_encode(self):
        res = bytearray()
        for record in self.records:
            res += record.encode()
        return res

    def build_response(self, pid):
        packet = Packet(None)
        self.header.build_response(packet, pid)
        rr = ResponseRecord(None)
        rr.rpid = self.header.pid
        rr.pr = constants.EGTS_PC_OK
        packet.records.append(rr)
        for record in self.records:
            record.build_response(packet)
        return packet.encode()
