import asyncio


class SimpleInstallerStarter:

    def __init__(self):
        self.adaptor = None
        self.installer = 'installer'

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
        class_desc = {'package_name': 'simple_installer', 'class': 'SimpleInstaller'}
        msg = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': self.installer})
        await self.adaptor.ask(msg)
        body = {"system_name": "local", "host": "192.168.100.170", "port": 6999, "ssh_port": 22,
                "username": "admin", "password": "adminadmin"}
        msg = self.adaptor.get_msg('add_server', body, self.installer)
        await self.adaptor.ask(msg, 300)
        head = self.adaptor.get_head_addr()
        self_addr = self.adaptor.get_self_addr()
        msg = self.adaptor.get_msg('subscribe', {'command': 'inter_linked'}, head, self_addr)
        await self.adaptor.send(msg)
        msg = self.adaptor.get_msg('connect', {'system_name': 'local'}, self.installer)
        await self.adaptor.send(msg)

    async def notification(self, msg):
        system_address = self.adaptor.get_addr('local', 'host.main.admin', None)
        body = {'package_desc': {'package_name': 'peacepie_example'}, 'recipient': system_address}
        request = self.adaptor.get_msg('deliver_package', body, self.adaptor.get_prime_addr())
        await self.adaptor.ask(request, 30)
        class_desc = {'package_name': 'peacepie_example', 'class': 'HelloWorld'}
        request = self.adaptor.get_msg('create_actor', {'class_desc': class_desc, 'name': 'second'})
        ans = await self.adaptor.ask(request)
        here = ans.get('body')
        request['recipient'] = self.adaptor.get_addr('local', 'host.main.admin', None)
        ans = await self.adaptor.ask(request, 10)
        there = ans.get('body') if ans.get('command') == 'actor_is_created' else None
        for i in range(9):
            request = self.adaptor.get_msg('tick', recipient=here)
            await self.adaptor.send(request)
            if there:
                request['recipient'] = there
                await self.adaptor.send(request)
            await asyncio.sleep(1)
        request = self.adaptor.get_msg('disconnect', {'system_name': 'local'}, self.installer)
        print('PRE_FINISH')
        await self.adaptor.send(request)
        print('FINISH')


