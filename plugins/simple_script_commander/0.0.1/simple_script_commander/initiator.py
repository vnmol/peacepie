

class SimpleScriptCommanderInitiator:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        piece = {'package_name': 'simple_script_commander', 'class': 'SimpleScriptCommanderReader'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': piece, 'name': 'reader'})
        await self.adaptor.ask(msg)
        piece = [{"name": "consumer", "value": "commander"}, {"name": "script_path", "value": "scripts"},
                 {"name": "period", "value": 4}]
        await self.adaptor.send(self.adaptor.get_msg('set_params', {'params': piece}, 'reader'))
        piece = {'package_name': 'simple_script_commander', 'class': 'SimpleScriptCommander'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': piece, 'name': 'commander'})
        await self.adaptor.ask(msg)
        await self.adaptor.send(self.adaptor.get_msg('start', recipient='reader'))
        print('READY')
