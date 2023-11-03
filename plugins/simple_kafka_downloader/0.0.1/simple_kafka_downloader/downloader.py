import asyncio

import aiokafka


class SimpleKafkaDownloader:

    def __init__(self):
        self.adaptor = None
        self.bootstrap_servers = None
        self.topic_name = None
        self.group_id = None
        self.kafka_consumer = None
        self.consumer = None

    async def handle(self, msg):
        if msg.command == 'set_params':
            self.set_params(msg.body['params'])
        elif msg.command == 'start':
            self.start()
        else:
            return False
        return True

    def set_params(self, params):
        for param in params:
            if param['name'] == 'bootstrap_servers':
                self.bootstrap_servers = param['value']
            elif param['name'] == 'topic_name':
                self.topic_name = param['value']
            elif param['name'] == 'group_id':
                self.group_id = param['value']
            elif param['name'] == 'consumer':
                if type(param['value']) is dict:
                    self.adaptor.add_to_cache(param['value']['node'], param['value']['entity'])
                    name = param['value']['entity']
                else:
                    name = param['value']
                self.consumer = name

    def start(self):
        asyncio.get_running_loop().create_task(self._start())

    async def _start(self):
        while True:
            is_connected = False
            try:
                self.kafka_consumer = aiokafka.AIOKafkaConsumer(
                    self.topic_name, bootstrap_servers=self.bootstrap_servers,
                    enable_auto_commit=False, group_id=self.group_id)
                await self.kafka_consumer.start()
                is_connected = True
            except Exception as e:
                self.adaptor.logger.exception(e)
            if not is_connected:
                await asyncio.sleep(20)
                continue
            try:
                async for msg in self.kafka_consumer:
                    if self.consumer:
                        message = self.adaptor.get_msg('navi_data', msg.value, recipient=self.consumer)
                        await self.adaptor.send(message)
                    await self.kafka_consumer.commit()
            finally:
                await self.kafka_consumer.stop()
