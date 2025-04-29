import random
import struct

from egts_convertor import constants
from egts_convertor.services.sub_record import SubRecord


class ResultCode(SubRecord):

    def __init__(self, parent, srl=None):
        super().__init__(parent, constants.EGTS_SR_RESULT_CODE, srl)
        self.rcd = None

    def decode(self, payload, pos):
        self.rcd, = struct.unpack_from("<B", payload, pos)
        pos += 1
        return pos

    def decode_with_print(self, payload, pos):
        result_codes = {
            constants.EGTS_PC_OK: "EGTS_PC_OK",
            constants.EGTS_PC_IN_PROGRESS: "EGTS_PC_IN_PROGRESS",
            constants.EGTS_PC_UNS_PROTOCOL: "EGTS_PC_UNS_PROTOCOL",
            constants.EGTS_PC_DECRYPT_ERROR: "EGTS_PC_DECRYPT_ERROR",
            constants.EGTS_PC_PROC_DENIED: "EGTS_PC_PROC_DENIED",
            constants.EGTS_PC_INC_HEADERFORM: "EGTS_PC_INC_HEADERFORM",
            constants.EGTS_PC_INC_DATAFORM: "EGTS_PC_INC_DATAFORM",
            constants.EGTS_PC_UNS_TYPE: "EGTS_PC_UNS_TYPE",
            constants.EGTS_PC_NOTEN_PARAMS: "EGTS_PC_NOTEN_PARAMS",
            constants.EGTS_PC_DBL_PROC: "EGTS_PC_DBL_PROC",
            constants.EGTS_PC_PROC_SRC_DENIED: "EGTS_PC_PROC_SRC_DENIED",
            constants.EGTS_PC_HEADERCRC_ERROR: "EGTS_PC_HEADERCRC_ERROR",
            constants.EGTS_PC_DATACRC_ERROR: "EGTS_PC_DATACRC_ERROR",
            constants.EGTS_PC_INVDATALEN: "EGTS_PC_INVDATALEN",
            constants.EGTS_PC_ROUTE_NFOUND: "EGTS_PC_ROUTE_NFOUND",
            constants.EGTS_PC_ROUTE_CLOSED: "EGTS_PC_ROUTE_CLOSED",
            constants.EGTS_PC_ROUTE_DENIED: "EGTS_PC_ROUTE_DENIED",
            constants.EGTS_PC_INVADDR: "EGTS_PC_INVADDR",
            constants.EGTS_PC_TTLEXPIRED: "EGTS_PC_TTLEXPIRED",
            constants.EGTS_PC_NO_ACK: "EGTS_PC_NO_ACK",
            constants.EGTS_PC_OBJ_NFOUND: "EGTS_PC_OBJ_NFOUND",
            constants.EGTS_PC_EVNT_NFOUND: "EGTS_PC_EVNT_NFOUND",
            constants.EGTS_PC_SRVC_NFOUND: "EGTS_PC_SRVC_NFOUND",
            constants.EGTS_PC_SRVC_DENIED: "EGTS_PC_SRVC_DENIED",
            constants.EGTS_PC_SRVC_UNKN: "EGTS_PC_SRVC_UNKN",
            constants.EGTS_PC_AUTH_DENIED: "EGTS_PC_AUTH_DENIED",
            constants.EGTS_PC_ALREADY_EXISTS: "EGTS_PC_ALREADY_EXISTS",
            constants.EGTS_PC_ID_NFOUND: "EGTS_PC_ID_NFOUND",
            constants.EGTS_PC_INC_DATETIME: "EGTS_PC_INC_DATETIME",
            constants.EGTS_PC_IO_ERROR: "EGTS_PC_IO_ERROR",
            constants.EGTS_PC_NO_RES_AVAIL: "EGTS_PC_NO_RES_AVAIL",
            constants.EGTS_PC_MODULE_FAULT: "EGTS_PC_MODULE_FAULT",
            constants.EGTS_PC_MODULE_PWR_FLT: "EGTS_PC_MODULE_PWR_FLT",
            constants.EGTS_PC_MODULE_PROC_FLT: "EGTS_PC_MODULE_PROC_FLT",
            constants.EGTS_PC_MODULE_SW_FLT: "EGTS_PC_MODULE_SW_FLT",
            constants.EGTS_PC_MODULE_FW_FLT: "EGTS_PC_MODULE_FW_FLT",
            constants.EGTS_PC_MODULE_IO_FLT: "EGTS_PC_MODULE_IO_FLT",
            constants.EGTS_PC_MODULE_MEM_FLT: "EGTS_PC_MODULE_MEM_FLT",
            constants.EGTS_PC_TEST_FAILED: "EGTS_PC_TEST_FAILED"
        }
        self.rcd, = struct.unpack_from("<B", payload, pos)
        print(" " * 12 + f"{payload[pos]:02X}".ljust(16) + f"RCD (Result Code)={result_codes.get(self.rcd)}")
        pos += 1
        print()
        return pos

    def encoding(self):
        res = bytearray()
        res += struct.pack("<B", self.rcd)
        return res


if __name__ == "__main__":
    origin = ResultCode(None)
    origin.rcd = random.randint(0, 0xFF)
    pl = origin.encoding()
    duplicate = ResultCode(None)
    duplicate.decode(pl, 0)
    assert origin == duplicate
