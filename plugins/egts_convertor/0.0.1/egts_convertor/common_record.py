import logging
import struct

from egts_convertor import constants
from egts_convertor.record_header import RecordHeader
from egts_convertor.services.auth_service.dispatcher_identity import DispatcherIdentity
from egts_convertor.services.auth_service.result_code import ResultCode
from egts_convertor.services.auth_service.term_identity import TermIdentity
from egts_convertor.services.sub_record import SubRecord
from egts_convertor.services.record_response import RecordResponse
from egts_convertor.services.teledata_service.abs_an_sens_data import AbsAnSensData
from egts_convertor.services.teledata_service.abs_cntr_data import AbsCntrData
from egts_convertor.services.teledata_service.abs_dig_sens_data import AbsDigSensData
from egts_convertor.services.teledata_service.abs_loopin_data import AbsLoopinData
from egts_convertor.services.teledata_service.accel_data import AccelData
from egts_convertor.services.teledata_service.ad_sensors_data import AdSensorsData
from egts_convertor.services.teledata_service.counters_data import CountersData
from egts_convertor.services.teledata_service.ext_pos_data import ExtPosData
from egts_convertor.services.teledata_service.liquid_level_sensor import LiquidLevelSensor
from egts_convertor.services.teledata_service.loopin_data import LoopinData
from egts_convertor.services.teledata_service.passengers_counters import PassengersCounters
from egts_convertor.services.teledata_service.pos_data import PosData
from egts_convertor.services.teledata_service.state_data import StateData
from egts_convertor.services.teledata_service.test_id_data import TestIdData


class CommonRecord:

    def __init__(self, parent):
        self.parent = parent
        self.header = RecordHeader(self)
        self.sub_records = []

    def __repr__(self):
        return f"{constants.service_types.get(self.header.rst)}({self.sub_records})"

    def decode(self, payload, pos):
        pos = self.header.decode(payload, pos)
        pos = self.sub_records_decode(payload, pos)
        return pos

    def sub_records_decode(self, payload, pos):
        while pos < len(payload):
            pos = self.sub_record_decode(payload, pos)
        return pos

    def sub_record_decode(self, payload, pos):
        srt, srl = struct.unpack_from("<BH", payload, pos)
        pos += 3
        sub_record = self.create_sub_record(srt, srl)
        old_pos = pos
        new_pos = sub_record.decode(payload, pos)
        pos = old_pos + srl
        if new_pos != pos:
            service = constants.sub_record_types.get(self.header.rst)
            sub_record_type = service.get(srt) if service else None
            logging.error(f'Class {sub_record.__class__.__name__} read {new_pos - old_pos} bytes, '
                          f'but the field "SRL" of the current subrecord {sub_record_type} has value {srl} bytes.')
        self.sub_records.append(sub_record)
        return pos

    def create_sub_record(self, srt, srl):
        match self.header.rst:
            case constants.EGTS_AUTH_SERVICE:
                match srt:
                    case constants.EGTS_SR_RECORD_RESPONSE:
                        return RecordResponse(self, srl)
                    case constants.EGTS_SR_TERM_IDENTITY:
                        return TermIdentity(self, srl)
                    case constants.EGTS_SR_MODULE_DATA:
                        pass
                    case constants.EGTS_SR_VEHICLE_DATA:
                        pass
                    case constants.EGTS_SR_DISPATCHER_IDENTITY:
                        return DispatcherIdentity(self, srl)
                    case constants.EGTS_SR_AUTH_PARAMS:
                        pass
                    case constants.EGTS_SR_AUTH_INFO:
                        pass
                    case constants.EGTS_SR_SERVICE_INFO:
                        pass
                    case constants.EGTS_SR_RESULT_CODE:
                        return ResultCode(self, srl)
            case constants.EGTS_TELEDATA_SERVICE:
                match srt:
                    case constants.EGTS_SR_RECORD_RESPONSE:
                        return RecordResponse(self, srl)
                    case constants.EGTS_SR_POS_DATA:
                        return PosData(self, srl)
                    case constants.EGTS_SR_EXT_POS_DATA:
                        return ExtPosData(self, srl)
                    case constants.EGTS_SR_AD_SENSORS_DATA:
                        return AdSensorsData(self, srl)
                    case constants.EGTS_SR_COUNTERS_DATA:
                        return CountersData(self, srl)
                    case constants.EGTS_SR_ACCEL_DATA:
                        return AccelData(self, srl)
                    case constants.EGTS_SR_STATE_DATA:
                        return StateData(self, srl)
                    case constants.EGTS_SR_LOOPIN_DATA:
                        return LoopinData(self, srl)
                    case constants.EGTS_SR_ABS_DIG_SENS_DATA:
                        return AbsDigSensData(self, srl)
                    case constants.EGTS_SR_ABS_AN_SENS_DATA:
                        return AbsAnSensData(self, srl)
                    case constants.EGTS_SR_ABS_CNTR_DATA:
                        return AbsCntrData(self, srl)
                    case constants.EGTS_SR_ABS_LOOPIN_DATA:
                        return AbsLoopinData(self, srl)
                    case constants.EGTS_SR_LIQUID_LEVEL_SENSOR:
                        return LiquidLevelSensor(self, srl)
                    case constants.EGTS_SR_PASSENGERS_COUNTERS:
                        return PassengersCounters(self, srl)
                    case constants.EGTS_SR_TEST_ID_DATA:
                         return TestIdData(self, srl)
            case constants.EGTS_COMMANDS_SERVICE:
                pass
            case constants.EGTS_FIRMWARE_SERVICE:
                pass
            case constants.EGTS_ECALL_SERVICE:
                pass
        return SubRecord(self, srt, srl)


    def decode_with_print(self, payload, pos):
        pos = self.header.decode_with_print(payload, pos)
        pos = self.sub_records_decode_with_print(payload, pos)
        return pos

    def sub_records_decode_with_print(self, payload, pos):
        while pos < len(payload):
            pos = self.sub_record_decode_with_print(payload, pos)
        return pos

    def sub_record_decode_with_print(self, payload, pos):
        srt, srl = struct.unpack_from("<BH", payload, pos)
        service = constants.sub_record_types.get(self.header.rst)
        sub_record_type = service.get(srt) if service else None
        print(" " * 8 + f"{payload[pos]:02X}".ljust(16) + f"SRT (Subrecord Type)={sub_record_type}")
        pos += 1
        print(" " * 8 + f"{payload[pos]:02X} {payload[pos + 1]:02X}".ljust(16) + "SRL (Subrecord Length)")
        pos += 2
        print()
        sub_record = self.create_sub_record(srt, srl)
        old_pos = pos
        new_pos = sub_record.decode_with_print(payload, pos)
        pos = old_pos + srl
        if new_pos != pos:
            logging.error(f'Class {sub_record.__class__.__name__} read {new_pos - old_pos} bytes, '
                          f'but the field "SRL" of the current subrecord {sub_record_type} has value {srl} bytes.')
        self.sub_records.append(sub_record)
        return pos

    def encode(self):
        res = bytearray()
        sub_records = self.sub_records_encode()
        res += self.header.encode(len(sub_records))
        res += sub_records
        return res

    def sub_records_encode(self):
        res = bytearray()
        for sub_record in self.sub_records:
            res += sub_record.encode()
        return res

    def build_response(self, packet):
        record = CommonRecord(packet)
        self.header.build_response(record.header)
        sub_record = RecordResponse(record, 0)
        sub_record.crn = self.header.rn
        sub_record.rst = constants.EGTS_PC_OK
        record.sub_records.append(sub_record)
        for sub_record in self.sub_records:
            sub_record.build_response(record)
        packet.records.append(record)
