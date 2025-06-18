import logging

from egts_convertor import constants
from egts_convertor.common_record import CommonRecord
from egts_convertor.packet import Packet
from egts_convertor.response_record import ResponseRecord
from egts_convertor.services.auth_service.term_identity import TermIdentity
from egts_convertor.services.auth_service.dispatcher_identity import DispatcherIdentity
from egts_convertor.services.teledata_service.pos_data import PosData
from egts_convertor.services.teledata_service.test_id_data import TestIdData
from egts_convertor.transformers.teledata_transformer import TeledataTransformer
from egts_convertor.transformers.auth_transformer import AuthTransformer


class EGTSConvertor:

    def __init__(self):
        self.adaptor = None
        self.mediator = None
        self.consumer = None
        self.code = None
        self.waiter = None
        self.current_address = 100
        self.data = b''
        self.pos = 0
        self.packet = Packet(self)
        self.pid = -1
        self.rn = -1

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'received_from_channel':
            await self.received_from_channel(body)
        elif command == 'send_to_channel':
            await self.send_to_channel(body, sender)
        elif command == 'set_params':
            await self.set_params(body, sender)
        elif command == 'start':
            await self.start(body)
        else:
            return False
        return True

    async def start(self, body):
        if body.get('is_client'):
            await self.authorize()
        else:
            await self.adaptor.send(self.adaptor.get_msg('channel_is_opened', None, self.mediator))


    async def set_params(self, body, recipient):
        params = body.get('params')
        if params is None:
            if recipient:
                await self.adaptor.send(self.adaptor.get_msg('params_are_not_set', None, recipient))
            return
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name == 'mediator':
                self.mediator = value
            elif name == 'consumer':
                self.consumer = value
            elif name == 'convertor_params':
                self.code = value.get('code')
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', None, recipient))

    async def received_from_channel(self, data):
        self.data += data
        try:
            while True:
                self.pos = self.packet.decode(self.data, self.pos)
                if self.packet.is_ready():
                    if self.packet.header.pt == constants.EGTS_PT_APPDATA:
                        response = self.packet.build_response(self.get_next_pid())
                        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', response, self.mediator))
                        await self.process()
                    elif self.packet.header.pt == constants.EGTS_PT_RESPONSE:
                        await self.response_process()
                else:
                    return
                self.packet = Packet(self)
                self.data = self.data[self.pos:]
                self.pos = 0
        except Exception as e:
            logging.exception(e)

    async def process(self):
        for record in self.packet.records:
            match record.header.rst:
                case constants.EGTS_AUTH_SERVICE:
                    self.code = AuthTransformer.transform(record).get('code')
                case constants.EGTS_TELEDATA_SERVICE:
                    navi = TeledataTransformer.transform(record)
                    navi['code'] = self.code if self.code else str(record.header.oid)
                    if navi:
                        await self.adaptor.send(self.adaptor.get_msg('navi_data', {'navi': navi}, self.consumer))

    async def response_process(self):
        if not self.waiter:
            return
        if len(self.packet.records) < 2:
            await self.error()
        else:
            record_0 = self.packet.records[0]
            record_1 = self.packet.records[1]
            if isinstance(record_0, ResponseRecord) and record_0.pr == constants.EGTS_PC_OK:
                match record_1.header.rst:
                    case constants.EGTS_AUTH_SERVICE:
                        await self.adaptor.send(self.adaptor.get_msg('channel_is_opened', None, self.waiter))
                    case constants.EGTS_TELEDATA_SERVICE:
                        await self.adaptor.send(self.adaptor.get_msg('sent', None, self.waiter))
                    case _:
                        await self.error()
                self.waiter = None
            else:
                await self.error()

    async def send_to_channel(self, body, recipient):
        if self.waiter:
            if recipient:
                await self.adaptor.send(self.adaptor.get_msg('connection_is_busy', recipient=recipient))
            return
        self.waiter = recipient
        if body is None:
            await self.error()
            return
        key = next(iter(body))
        match key:
            case 'navi':
                await self.send_navi_to_channel(body)
            case _:
                await self.error()

    async def send_navi_to_channel(self, body):
        navi = body.get('navi')
        packet = Packet(None)
        packet.header.set(self.get_next_pid(), pt=constants.EGTS_PT_APPDATA)
        record = CommonRecord(packet)
        record.header.set(self.get_next_rn(), 1, 0, constants.EGTS_TELEDATA_SERVICE, constants.EGTS_TELEDATA_SERVICE)
        code = self.code if self.code else navi.get('code')
        code = code[len(code) - 8:]
        try:
            oid = int(code)
        except ValueError:
            try:
                oid = hash(code) & 0xFFFFFFFF
            except TypeError:
                await self.error()
                return
        record.header.oid = oid
        sub_record = PosData(record)
        sub_record.set_lat(navi.get('lat'))
        sub_record.set_long(navi.get('lon'))
        sub_record.set_datetime(navi.get('datetime'))
        sub_record.set_spd(navi.get('speed'))
        if sub_record.get_spd() > 3:
            sub_record.set_mv(1)
        sub_record.set_fix(1)
        sub_record.set_vld(1)
        record.sub_records.append(sub_record)
        if navi.get('id') is not None:
             sub_record = TestIdData(record)
             sub_record.set_id(navi.get('id'))
             record.sub_records.append(sub_record)
        packet.records.append(record)
        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', packet.encode(), self.mediator))

    async def authorize(self):
        self.waiter = self.mediator
        packet = Packet(None)
        packet.header.set(self.get_next_pid(), constants.EGTS_PT_APPDATA)
        record = CommonRecord(packet)
        record.header.set(self.get_next_rn(), 1, 0, constants.EGTS_AUTH_SERVICE, constants.EGTS_AUTH_SERVICE)
        if self.code:
            sub_record = TermIdentity(record)
            sub_record.set_imei(self.code)
        else:
            sub_record = DispatcherIdentity(record)
            sub_record.init()
        record.sub_records.append(sub_record)
        packet.records.append(record)
        await self.adaptor.send(self.adaptor.get_msg('send_to_channel', packet.encode(), self.mediator))

    async def error(self, txt=None):
        if not self.waiter:
            return
        data = {'txt': txt} if txt else None
        await self.adaptor.send(self.adaptor.get_msg('error', data, self.waiter))
        self.waiter = None

    def get_next_pid(self):
        self.pid = self.pid + 1 if self.pid < 65535 else 0
        return self.pid

    def get_next_rn(self):
        self.rn = self.rn + 1 if self.rn < 65535 else 0
        return self.pid
