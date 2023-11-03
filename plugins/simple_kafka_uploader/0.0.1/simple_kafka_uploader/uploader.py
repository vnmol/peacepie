import kafka
import aiokafka


class SimpleKafkaUploader:

    def __init__(self):
        self.adaptor = None
        self.bootstrap_servers = None
        self.topic_name = None
        self.producer = None

    async def handle(self, msg):
        command = msg['command']
        if command == 'bytes':
            await self.bytes(msg['body'])
        elif command == 'start':
            await self.start()
        elif command == 'set_params':
            await self.set_params(msg)
        else:
            return False
        return True

    async def bytes(self, data):
        if not self.producer:
            await self.start()
        try:
            await self.producer.send_and_wait(self.topic_name, data)
        except Exception as e:
            self.adaptor.logger.exception(e)
            await self.producer.stop()
            self.producer = None

    async def start(self):
        admin_client = kafka.KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
        if self.topic_name in [topic for topic in admin_client.list_topics()]:
            self.adaptor.logger.info(f'Kafka topic "{self.topic_name}" exists')
        else:
            try:
                new_topic = kafka.admin.NewTopic(name=self.topic_name, num_partitions=1, replication_factor=1)
                admin_client.create_topics(new_topics=[new_topic])
                self.adaptor.logger.info(f'Kafka topic "{self.topic_name}" created successfully')
                admin_client.close()
            except kafka.errors.TopicAlreadyExistsError:
                self.adaptor.logger.error(f'Kafka topic "{self.topic_name}" exists')
        admin_client.close()
        self.producer = aiokafka.AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self.producer.start()

    async def set_params(self, msg):
        for param in msg['body']['params']:
            if param['name'] == 'bootstrap_servers':
                self.bootstrap_servers = param['value']
            elif param['name'] == 'topic_name':
                self.topic_name = param['value']
        ans = self.adaptor.get_msg('params_are_set', recipient=msg['sender'])
        await self.adaptor.send(ans)
