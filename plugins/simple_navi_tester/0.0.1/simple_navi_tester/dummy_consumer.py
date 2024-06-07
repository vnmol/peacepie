class DummyConsumer:

    def __init__(self):
        self.adaptor = None

    async def pre_run(self):
        await self.adaptor.cumulative_commands_set(['navi_send'])
        self.adaptor.not_log_commands.update(['sent', 'cumulative_tick'])

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'navi_data':
            pass
        elif command == 'navi_send':
            await self.adaptor.send(self.adaptor.get_msg('sent', None, msg.get('sender')))
        else:
            return False
        return True
