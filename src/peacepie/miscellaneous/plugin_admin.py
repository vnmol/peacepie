import importlib.util
import os
import sys

from peacepie import params


class PluginAdmin:

    def __init__(self):
        self.actor = None
        self.modules = {}
        path = params.instance['plugins_path']
        self.path = path if path.endswith('/') else path + '/'

    async def handle(self, msg):
        if msg.command == 'get_class':
            answer = self.actor.get_msg('class', self.get_class(msg.body), msg.sender)
            await self.actor.send(msg.sender, answer)
        else:
            return False
        return True

    def get_class(self, jsn):
        res = None
        module = self.get_module(jsn)
        if module is None:
            return None
        try:
            res = getattr(module, jsn['class'])
        except Exception as ex:
            self.actor.logger.exception(ex)
        return res

    def get_module(self, jsn):
        path = jsn['path']
        if path != '' and not path.endswith('/'):
            path = path + '/'
        fullpath = os.path.abspath(self.path + path + jsn['package'] + '/' + jsn['module'] + '.py')
        module = self.modules.get(fullpath)
        if module is None:
            try:
                self.actor.logger.info(f'Try to load module from the path "{fullpath}"')
                spec = importlib.util.spec_from_file_location(jsn['mod_name'], fullpath)
                module = importlib.util.module_from_spec(spec)
                sys.modules[jsn['mod_name']] = module
                spec.loader.exec_module(module)
            except Exception as ex:
                self.actor.logger.exception(ex)
                return None
        return module
