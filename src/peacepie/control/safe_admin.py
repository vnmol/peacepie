import logging

from peacepie import params, msg_factory
from peacepie.assist import log_util, json_util


def load_credentials():
    res = None
    try:
        with open(params.instance.get('safe_config'), 'r') as file:
            json = file.read()
        res = json_util.json_loads(json)
    except Exception as e:
        logging.exception('safe_config_read_error', e)
    return res


class SafeAdmin:

    def __init__(self, parent):
        self.parent = parent
        self.credentials = load_credentials()
        self.not_log_commands = set()
        self.cumulative_commands = {}
        logging.info(log_util.get_alias(self) + ' is created')

    async def handle(self, msg):
        logging.debug(log_util.async_received_log(self, msg))
        command = msg.get('command')
        if command == 'get_credentials':
            body = msg.get('body') if isinstance(msg.get('body'), dict) else {}
            body = self.credentials.get(body.get('credentials_name'))
            ans = msg_factory.get_msg('credentials', body, msg.get('sender'))
            await self.parent.adaptor.send(ans, self)
        else:
            logging.warning(log_util.get_alias(self) + ' The message is not handled: ' + str(msg))
