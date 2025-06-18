from egts_convertor import constants


class TeledataTransformer:

    @staticmethod
    def transform(record):
        res = {}
        for sr in record.sub_records:
            match sr.srt:
                case constants.EGTS_SR_POS_DATA:
                    res['datetime'] = sr.get_datetime()
                    res['lat'] = sr.get_lat()
                    res['lon'] = sr.get_long()
                case constants.EGTS_SR_TEST_ID_DATA:
                    res['id'] = sr.get_id()
        return res
