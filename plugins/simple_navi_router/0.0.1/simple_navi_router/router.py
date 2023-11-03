
class SimpleNaviRouter:

    def __init__(self):
        self.adaptor = None
        self.listeners = {}

    async def handle(self, msg):
        if msg.command == 'navi_data':
            await self.navi_data(msg)
        elif msg.command == 'subscribe':
            await self.subscribe(msg)
        else:
            return False
        return True

    async def navi_data(self, msg):
        data = msg.body
        key = (data['key']['type'], data['key']['code'])
        listeners = self.listeners.get(key)
        for listener in listeners:
            msg.recipient = listener
            await self.adaptor.send(msg)

    async def subscribe(self, msg):
        subscribe_desc = msg.body
        key = (subscribe_desc['key']['type'], subscribe_desc['key']['code'])
        subscriber = subscribe_desc['subscriber']
        res = self.listeners.get(key)
        if not res:
            res = set()
            self.listeners[key] = res
        self.adaptor.add_to_cache(subscriber['node'], subscriber['entity'])
        res.add(subscriber['entity'])
        await self.adaptor.send(self.adaptor.get_msg('subscribed', recipient=msg.sender))
