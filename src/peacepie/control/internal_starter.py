import os
import re

from peacepie import msg_factory, params
from peacepie.assist import dir_operations


class InternalStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'start':
            await self.start()
        elif command == 'app_starter':
            await self.app_starter(msg)
        else:
            return False
        return True

    async def start(self):
        package_path = params.instance.get('starter')
        package_name = os.path.basename(package_path)
        ans = await self.adaptor.ask(self.adaptor.get_msg('get_source_path'))
        body = ans.get('body')
        if not body:
            return
        dst = f'{body.get("path")}/{package_name}'
        # shutil.copy(package_path, dst)
        dir_operations.copy_file(package_path, dst)
        package_name = package_name.split('.')[0]
        class_desc = {'package_name': package_name, 'class': None}
        msg = msg_factory.get_msg('create_actor', {'class_desc': class_desc, 'name': 'starter'})
        ans = await self.adaptor.ask(msg)
        command = ans.get('command')
        if command != 'actor_is_created':
            return
        body = {'internal_starter': self.adaptor.get_self_addr()}
        msg = msg_factory.get_msg('start', body, recipient=ans.get('body'))
        await self.adaptor.send(msg)

    async def app_starter(self, msg):
        body = msg.get('body')
        name = body.get('name')
        pattern = f'async\s+def\s+{name}\(self,\s*msg\s*\):'
        with open(params.instance.get('starter'), 'r') as file:
            lines = file.readlines()
        beg = None
        end = len(lines)
        for i, line in enumerate(lines):
            if beg:
                if re.search(pattern, line):
                    end = i
                    break
            else:
                if re.search(pattern, line):
                    beg = i
                    pattern = 'def\s+\w+\(.*\):'
        if beg:
            lines[beg+1:end] = self.change_leading_spaces(lines[beg], body.get('txt'))
            with open(params.instance.get('starter'), 'w') as file:
                file.writelines(lines)
            await self.adaptor.send(self.adaptor.get_msg('app_starter_is_ready', recipient=msg.get('sender')))
        else:
            await self.adaptor.send(self.adaptor.get_msg('app_starter_is_not_ready', recipient=msg.get('sender')))

    def change_leading_spaces(self, anchor, txt):
        res = txt.split('\n')
        res = [line + '\n' for line in res if line.strip()]
        dx = len(anchor) - len(anchor.lstrip()) + 4
        dx -= len(res[0]) - len(res[0].lstrip())
        res = [' ' * (len(line) - len(line.lstrip()) + dx) + line.lstrip() for line in res]
        res.append('\n')
        return res
