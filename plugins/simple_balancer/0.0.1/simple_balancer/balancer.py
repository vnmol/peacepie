
IS_LOADED = 'is_loaded'
IS_AVAILABLE = 'is_available'
CAN_DEPLOY = 'can_deploy'
MQL = 'max_queue_length'
QLS = 'queue_length_sum'
COUNT = 'count'
HOST = 'host'
IS_PRIME = 'is_prime'
DELTA = 'delta'
SENDER = 'sender'
NEW_PROCESS = 'new_process'

ITEM = 'item'
SCORE = 'score'

WEIGHTS = {IS_LOADED: 1, IS_AVAILABLE: 1, MQL: 1, QLS: 1, COUNT: 1, DELTA: 1}
W = sum(WEIGHTS.values())

E = 1


class Balancer:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg.command == 'create_actor':
            await self.create_actor(msg)
        else:
            return False
        return True

    async def create_actor(self, msg):
        dependency_desc = await self.get_dependencies(msg.body)
        fields = {IS_LOADED, IS_AVAILABLE, CAN_DEPLOY, MQL, QLS, COUNT, HOST, IS_PRIME, DELTA}
        body = {'params': {'class_desc': msg.body['class_desc'], 'dependency_desc': dependency_desc}, 'fields': fields}
        answer = await self.adaptor.ask(self.adaptor.get_msg('gather_info', body))
        scoring(answer.body, msg)
        sender = msg.sender
        answer = await self.adaptor.ask(msg, 40)
        answer.recipient = sender
        await self.adaptor.send(answer)

    async def get_dependencies(self, class_desc):
        msg = self.adaptor.get_msg('get_dependencies', class_desc,
                                   recipient='head.main.admin')
        ans = await self.adaptor.ask(msg)
        if ans.command == 'dependencies':
            return ans.body
        return


def scoring(items, msg):
    res = {SENDER: None, SCORE: 0}
    hosts = {}
    for item in items:
        if item[IS_LOADED]:
            score = WEIGHTS[IS_LOADED] / (item[IS_LOADED] + E)
        else:
            score = WEIGHTS[IS_AVAILABLE] / (item[IS_AVAILABLE] + E)
        score += WEIGHTS[MQL] / (item[MQL] + E) + WEIGHTS[QLS] / (item[QLS] + E)
        score += WEIGHTS[COUNT] / (item[COUNT] + E) + WEIGHTS[DELTA] / (item[DELTA] + E)
        score = score / W
        if hosts.get(item[HOST]) is None:
            hosts[item[HOST]] = {SENDER: None, SCORE: 0}
        if item[IS_PRIME]:
            hosts[item[HOST]][SENDER] = item[SENDER]
        hosts[item[HOST]][SCORE] += score
        if item[CAN_DEPLOY] or item[IS_LOADED]:
            if score > res[SCORE]:
                res[SENDER] = item[SENDER]
                res[SCORE] = score
    if res[SENDER] is None:
        msg.command = 'produce_actor'
        for host in hosts.values():
            if host[SCORE] > res[SCORE]:
                res[SENDER] = host[SENDER]
                res[SCORE] = host[SCORE]
    msg.recipient = res[SENDER]
