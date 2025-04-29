import struct

from egts_convertor import constants


class ResponseRecord:

    def __init__(self, parent):
        self.parent = parent
        self.rpid = None
        self.pr = None


    def __repr__(self):
        return f'{constants.service_types.get(constants.EGTS_RECORD_RESPONSE)}(rpid={self.rpid}, pr={self.pr})'

    def decode(self, payload, pos):
        self.rpid, self.pr = struct.unpack_from('<HB', payload, pos)
        pos += 3
        return pos

    def decode_with_print(self, payload, pos):
        self.rpid, self.pr = struct.unpack_from('<HB', payload, pos)
        print(' ' * 4 + f'{payload[pos]:02X} {payload[pos + 1]:02X}'.ljust(16) + 'RPID (Response Packet ID)')
        pos += 2
        print(' ' * 4 + f'{payload[pos]:02X}'.ljust(16) + f'PR(Processing Result)={constants.response_types.get(self.pr)}')
        pos += 1
        print()
        return pos

    def encode(self):
        res = bytearray()
        res += struct.pack("<HB", self.rpid, self.pr)
        return res
