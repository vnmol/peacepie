import asyncio
import logging
import platform

from peacepie import adaptor, params, multimanager, loglistener, msg_factory, log_conf
from peacepie.assist import log_util, json_util, version
from peacepie.control import head_prime_admin, prime_admin


class PeaceSystem:

    def __init__(self, path, test_params=None):
        # json_util.init(json_package)
        params.init_params(path, test_params)
        log_conf.logger_start(params.instance.get('log_config'))
        logging.info(f'System-Version: {platform.system()} {platform.version()}')
        logging.info(f'Python-Version: {version.version_to_string(version.get_python_version())}')
        logging.info(f'Peacepie-Version: {params.instance.get("peacepie_version")}')
        json_util.init()
        self.is_head = params.instance.get('intra_role') == 'master'
        self.host_name = params.instance.get('host_name')
        self.process_name = params.instance.get('process_name')
        self.prefix = self.host_name + '.' + self.process_name + '.'
        multimanager.init_multimanager(self.prefix + 'multimanager')
        loglistener.init_loglistener(self.prefix + 'loglistener')
        self.name = self.prefix + 'system'
        msg_queue = multimanager.instance.get_queue()
        msg_queue.put(0)
        self.task = None
        self.test_errors = []
        msg_factory.init_msg_factory(self.host_name, self.process_name, 'msg_factory', msg_queue)
        logging.info(log_util.get_alias(self) + ' is created')

    async def start(self):
        if self.is_head:
            performer = head_prime_admin.HeadPrimeAdmin(self, self.host_name, self.process_name)
        else:
            performer = prime_admin.PrimeAdmin(self.host_name, self.process_name)
        actr = adaptor.Adaptor(None, self.prefix + 'admin', None, performer)
        self.task = asyncio.get_running_loop().create_task(actr.run())

    def set_test_error(self, res):
        self.test_errors.append(res)
