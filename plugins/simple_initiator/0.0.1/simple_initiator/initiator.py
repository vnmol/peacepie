import asyncio


def get_config(file):
    with open(file) as f:
        return [line.strip().split('#')[0] for line in f.readlines()]


class SimpleInitiator:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg.command == 'start':
            await self.start(msg)
        else:
            return False
        return True

    async def start(self, msg):
        data = await asyncio.get_running_loop().run_in_executor(None, get_config, msg.body['command_file'])
        for cmd in data:
            cmd = cmd.strip()
            if cmd == '':
                continue
            jsn = self.adaptor.json_loads(cmd)
            if jsn is None:
                continue
            if jsn['command'] == 'sleep':
                await asyncio.sleep(jsn['body']['period'])
            else:
                msg = self.adaptor.get_msg(jsn['command'], jsn['body'])
                msg.recipient = jsn.get('recipient')
                if jsn.get('is_ask'):
                    await self.adaptor.ask(msg, 30)
                else:
                    await self.adaptor.send(msg)
        await self.adaptor.send(self.adaptor.get_msg('actor_destroyed', self.adaptor.name))
        print('Initiator: "READY"')
