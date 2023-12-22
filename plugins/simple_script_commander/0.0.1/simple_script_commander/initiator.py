class SimpleScriptCommanderInitiator:

    def __init__(self):
        self.adaptor = None
        self.commander = 'commander'

    async def handle(self, msg):
        command = msg.get('command')
        if not command:
            return None
        if command == 'start':
            await self.start()
        elif command == 'notification':
            await self.notification(msg)
        else:
            return False
        return True

    async def start(self):
        class_desc = {'package_name': 'simple_script_commander', 'class': 'SimpleScriptCommander'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': self.commander})
        await self.adaptor.ask(msg)
        ''
        body = {"system_name": "local", "host": "192.168.100.164", "port": 6999, "ssh_port": 22,
                "username": "vmol", "password": "NewZeland1"}
        msg = self.adaptor.get_msg('add_server', body, self.commander)
        await self.adaptor.ask(msg, 10)
        ''
        head = self.adaptor.get_head_addr()
        self_addr = self.adaptor.get_self_addr()
        msg = self.adaptor.get_msg('subscribe', {'command': 'inter_linked'}, head, self_addr)
        await self.adaptor.send(msg)
        msg = self.adaptor.get_msg('connect', {'system_name': 'local'}, self.commander)
        await self.adaptor.send(msg)

    async def notification(self, msg):
        system_address = self.adaptor.get_addr('local', 'host.main.admin', None)
        body = {'package_desc': {'package_name': 'peacepie_example'}, 'recipient': system_address}
        request = self.adaptor.get_msg('deliver_package', body, self.adaptor.get_prime_addr())
        await self.adaptor.ask(request, 30)
        class_desc = {'package_name': 'peacepie_example', 'class': 'HelloWorld'}
        request = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'first'}, system_address)
        await self.adaptor.ask(request, 10)
        request = self.adaptor.get_msg('disconnect', {'system_name': 'local'}, self.commander)
        print('PRE_FINISH')
        await self.adaptor.send(request)
        print('FINISH')


