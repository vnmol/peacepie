import enum
import logging

from egts_convertor import constants
from egts_convertor.common_record import CommonRecord
from egts_convertor.packet import Packet
from egts_convertor.response_record import ResponseRecord
from egts_convertor.services.auth_service.term_identity import TermIdentity
from egts_convertor.services.teledata_service.pos_data import PosData


class EGTSConvertor:

    def __init__(self):
        self.adaptor = None
        self.waiter = None
        self.mediator = None
        self.consumer = None
        self.current_address = 100
        self.data = b''
        self.pos = 0
        self.packet = Packet(self)
        self.pid = -1
        self.rn = -1

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        if command == 'received_from_channel':
            await self.received_from_channel(body)
        elif command == 'send_to_channel':
            await self.send_to_channel(body)
        elif command == 'channel_is_opened':
            await self.channel_is_opened(body, msg.get('sender'))
        elif command == 'set_params':
            await self.set_params(body.get('params'), msg.get('sender'))
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'mediator':
                self.mediator = value
            elif name == 'consumer':
                self.consumer = value
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def channel_is_opened(self, data, waiter):
        self.waiter = waiter
        imei = data.get('imei')
        packet = Packet(None)
        packet.header.set(self.get_next_pid(), constants.EGTS_PT_APPDATA)
        record = CommonRecord(packet)
        record.header.set(self.get_next_rn(), 1, 0, constants.EGTS_AUTH_SERVICE, constants.EGTS_AUTH_SERVICE)
        sub_record = TermIdentity(record)
        sub_record.set(imei)
        record.sub_records.append(sub_record)
        packet.records.append(record)
        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', packet.encode(), self.mediator))

    async def received_from_channel(self, data):
        self.data += data
        try:
            while True:
                self.pos = self.packet.decode(self.data, self.pos)
                if self.packet.is_ready():
                    if self.packet.header.pt == constants.EGTS_PT_APPDATA:
                        response = self.packet.build_response(self.get_next_pid())
                        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', response, self.mediator))
                    elif self.packet.header.pt == constants.EGTS_PT_RESPONSE:
                        if len(self.packet.records) > 0:
                            sub_record = self.packet.records[0]
                            if isinstance(sub_record, ResponseRecord):
                                if sub_record.pr == constants.EGTS_PC_OK:
                                    if self.waiter:
                                        await self.adaptor.send(self.adaptor.get_msg('OK', None, self.waiter))
                else:
                    return
                self.packet = Packet(self)
                self.data = self.data[self.pos:]
                self.pos = 0
        except Exception as e:
            logging.exception(e)

    async def send_to_channel(self, data):
        navi = data.get('navi')
        packet = Packet(None)
        packet.header.set(self.get_next_pid(), pt=constants.EGTS_PT_APPDATA)
        record = CommonRecord(packet)
        record.header.set(self.get_next_rn(), 1, 0, constants.EGTS_TELEDATA_SERVICE, constants.EGTS_TELEDATA_SERVICE)
        sub_record = PosData(record)
        sub_record.set_lat(navi.get('lat'))
        sub_record.set_long(navi.get('lon'))
        sub_record.set_datetime(navi.get('time'))
        record.sub_records.append(sub_record)
        packet.records.append(record)
        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', packet.encode(), self.mediator))

    def get_next_pid(self):
        self.pid = self.pid + 1 if self.pid < 65535 else 0
        return self.pid

    def get_next_rn(self):
        self.rn = self.rn + 1 if self.rn < 65535 else 0
        return self.pid
