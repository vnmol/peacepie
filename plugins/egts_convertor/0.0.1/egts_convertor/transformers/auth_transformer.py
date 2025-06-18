from egts_convertor import constants

from egts_convertor.services.auth_service.term_identity import TermIdentity


class AuthTransformer:

    @staticmethod
    def transform(record):
        res = {}
        for sr in record.sub_records:
            match sr.srt:
                case constants.EGTS_SR_TERM_IDENTITY:
                    res['code'] = sr.imei
        return res
