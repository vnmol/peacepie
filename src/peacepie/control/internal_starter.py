import os

from peacepie import msg_factory, params
from peacepie.assist import dir_opers


class InternalStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        await self.account_admin()
        src = os.path.abspath(params.instance.get('starter'))
        package_name = os.path.basename(src)
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_work_path'))
        body = ans.get('body')
        if not body:
            return
        dst = os.path.abspath(f'{body.get("path")}/{package_name}')
        os.symlink(src, dst)
        package_name = package_name.split('.')[0]
        msg = msg_factory.get_msg('create_actor', {'class_desc': {'requires_dist': package_name}, 'name': 'starter'})
        ans = await self.adaptor.ask(msg)
        command = ans.get('command')
        if command != 'actor_is_created':
            return
        body = {'internal_starter': self.adaptor.get_self_addr()}
        msg = msg_factory.get_msg('start', body, recipient=ans.get('body'))
        await self.adaptor.send(msg)
        await self.adaptor.send(self.adaptor.get_msg('remove_actor', {'name': self.adaptor.name}))

    async def account_admin(self):
        name = 'account_admin'
        body = {'class_desc': {'requires_dist': 'peacepie.control.accounts.account_admin'}, 'name': name}
        ans = await self.adaptor.ask(self.adaptor.get_msg('create_actor', body))
        if ans.get('command') == 'actor_is_created':
            await self.adaptor.ask(self.adaptor.get_msg('start', None, name))
