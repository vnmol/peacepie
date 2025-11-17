import asyncio
import logging
import multiprocessing
import importlib.metadata
import os

from peacepie import adaptor, msg_factory, params

from peacepie.assist import auxiliaries, dir_opers, log_util, timer, version

index = 0
replica_index = 0

shared_folders = {'__pycache__', 'bin'}

class VersionError(Exception):
    pass



class ActorCreator:

    def __init__(self, parent):
        global index
        self.name = f'actor_loader_{index}'
        index += 1
        self.parent = parent
        self.grandparent = parent.parent
        self.queue = asyncio.Queue()
        self.not_log_commands = set()
        self.cumulative_commands = {}
        logging.info(log_util.get_alias(self) + ' is created')

    async def run(self):
        while True:
            msg = await self.queue.get()
            logging.debug(log_util.async_received_log(self, msg))
            try:
                if not await self.handle(msg):
                    logging.warning(log_util.get_alias(self) + ': The message is not handled: ' + str(msg))
            except Exception as ex:
                logging.exception(ex)

    async def handle(self, msg):
        command = msg.get('command')
        if command == 'create_actor':
            await self.create_actor(msg, False)
        elif command == 'create_replica':
            await self.create_actor(msg, True)
        elif command == 'create_actors':
            await self.create_actors(msg)
        else:
            return False
        return True

    async def redirect(self, msg):
        sender = msg.get('sender')
        if msg.get('body').get('is_only'):
            await self.inform('actor_is_not_created', sender)
            return None
        msg.get('body')['is_only'] = True
        nodes = await self.grandparent.adaptor.get_local_nodes(exclude_current=True)
        for node in nodes:
            msg['recipient'] = node
            ans = await self.grandparent.adaptor.ask(msg, questioner=self)
            if ans.get('command') == 'actor_is_created':
                await self.inform('actor_is_created', sender)
                return None
        query = msg_factory.get_msg('create_process', None, self.grandparent.adaptor.get_head_addr())
        ans = await self.grandparent.adaptor.ask(query)
        if ans.get('command') != 'actor_is_created':
            return None
        msg['recipient'] = ans.get('body')
        ans = await self.grandparent.adaptor.ask(msg, questioner=self)
        await self.inform(ans.get('command'), sender)
        return None

    async def inform(self, command, recipient):
        if recipient is None:
            return
        await self.grandparent.adaptor.send(msg_factory.get_msg(command, None, recipient), self)

    def create_package_info(self, package_name, ver):
        package_info_path = f'{self.parent.work_path}/{package_name}-{ver}.dist-info'
        dir_opers.recreatedir(package_info_path)
        with open(f'{package_info_path}/METADATA', 'w', encoding='utf-8') as f:
                 f.write(f'Name: {package_name}\n')
                 f.write(f'Version: {ver}\n')

    def developing_symlink(self, package_name, version_spec, class_name):
        path = f'{params.instance.get("plugin_dir")}/{package_name}'
        vers = [name for name in os.listdir(path) if version.version_from_string(name)]
        ver = version.find_max_version(vers, version_spec)
        source_path = f'{path}/{ver}'
        if dir_opers.is_dir_exist(f'{source_path}/src'):
            source_path = f'{source_path}/src/{package_name}'
        else:
            source_path = f'{source_path}/{package_name}'
        if dir_opers.sync_create_symlink(source_path, f'{self.parent.work_path}/{package_name}'):
            self.create_package_info(package_name, ver)
            pack = importlib.import_module(package_name)
            return getattr(pack, class_name)
        return None

    async def load_and_get(self, msg):
        class_desc = msg.get('body').get('class_desc')
        requires_dist = class_desc.get('requires_dist')
        parsed_requires_dist = version.parse_requires_dist(requires_dist)
        if params.instance.get('developing_mode'):
            package_name = parsed_requires_dist.get('package_name')
            version_spec = parsed_requires_dist.get('version_spec')
            res = self.developing_symlink(package_name, version_spec, class_desc.get('class'))
            if res:
                return res
        body = {'requires_dist': requires_dist, 'extra-index-url': class_desc.get('extra-index-url')}
        recipient = self.grandparent.adaptor.get_head_addr()
        query = msg_factory.get_msg('load_package', body, recipient, timeout=msg.get('timeout'))
        ans = await self.grandparent.adaptor.ask(query, questioner=self)
        if ans.get('command') != 'package_is_loaded':
            return None
        entry = ans.get('body').get('entry')
        source_path = params.instance.get('source_path')
        packages = get_link_list(source_path, self.parent.work_path, parsed_requires_dist, entry)
        if link_packages(source_path, self.parent.work_path, packages):
            return get_class(msg)
        return None

    async def try_another_way(self, is_absent, msg):
        if is_absent:
            try:
                res = await self.load_and_get(msg)
                if res:
                    return res
            except Exception as e:
                logging.exception(e)
        try:
            return await self.redirect(msg)
        except Exception as e:
            logging.exception(e)
        return None

    async def get_class(self, msg):
        try:
            return get_class(msg)
        except VersionError:
            is_absent = False
        except importlib.metadata.PackageNotFoundError:
            is_absent = True
        except Exception as e:
            logging.exception(e)
            command = 'actor_is_not_created' if msg.get('command') == 'create_actor' else 'actors_are_not_created'
            await self.grandparent.adaptor.send(msg_factory.get_msg(command, recipient=msg.get('sender')), self)
            return None
        return await self.try_another_way(is_absent, msg)

    async def create_actor(self, msg, is_replica):
        global replica_index
        body = msg.get('body') if msg.get('body') else {}
        class_desc = body.get('class_desc')
        name = body.get('name')
        if self.parent.actors.get(name) and not is_replica:
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
            await self.grandparent.adaptor.send(answer, self)
            return
        real_name = name
        if is_replica and name is None:
            real_name = (f'replica_{self.grandparent.adaptor.get_param("host_name")}_'
                         f'{multiprocessing.current_process().name}_{replica_index}')
            replica_index += 1
        try:
            clss = await self.get_class(msg)
            if not clss:
                return
            adptr = adaptor.Adaptor(class_desc, real_name, self.grandparent, clss(), msg.get('sender'))
            if is_replica:
                adptr.pause_event = asyncio.Event()
        except Exception as e:
            logging.exception(e)
            answer = msg_factory.get_msg('actor_is_not_created', recipient=msg.get('sender'))
            await self.grandparent.adaptor.send(answer, self)
            return
        task = asyncio.get_running_loop().create_task(adptr.run())
        self.parent.actors[real_name] = {'adaptor': adptr, 'task': task}

    async def create_actors(self, msg):
        clss = await self.get_class(msg)
        if not clss:
            return
        queue = asyncio.Queue()
        actors = {}
        body = msg.get('body') if msg.get('body') else {}
        class_desc = body.get('class_desc')
        if not body:
            return
        names = body.get('names')
        if not names:
            return
        for name in names:
            try:
                adptr = adaptor.Adaptor(class_desc, name, self.grandparent, clss(), queue)
                task = asyncio.get_running_loop().create_task(adptr.run())
                actors[name] = {'adaptor': adptr, 'task': task}
            except Exception as e:
                logging.exception(e)
                await self.clear(actors, msg.get('sender'))
                return
        timeout = msg.get('timeout')
        if not timeout:
            timeout = 1
        timer.start(timeout, queue, msg.get('mid'))
        count = 0
        while True:
            if count == len(actors):
                break
            ans = await queue.get()
            logging.debug(log_util.async_received_log(self, ans))
            if ans.get('command') != 'actor_is_created':
                break
            count += 1
        if count < len(actors):
            await self.clear(actors, msg.get('sender'))
            return
        self.parent.actors.update(actors)
        node = self.grandparent.adaptor.name
        body = {'node': node, 'names': names}
        ans = msg_factory.get_msg('actors_are_created', body, msg.get('sender'))
        await self.grandparent.adaptor.send(ans, self)

    async def clear(self, actors, recipient):
        for actor in actors:
            actor['task'].cancel()
        ans = msg_factory.get_msg('actors_are_not_created', recipient=recipient)
        await self.grandparent.adaptor.send(ans, self)


def get_class(msg):
    class_desc = msg.get('body').get('class_desc')
    requires_dist = version.parse_requires_dist(class_desc.get('requires_dist'))
    package_name = requires_dist.get('package_name')
    version_spec = requires_dist.get('version_spec')
    if not class_desc.get('class'):
        pack = importlib.import_module(package_name)
        return auxiliaries.get_primary_class(pack)
    ver = importlib.metadata.version(package_name)
    if not version.check_version(ver, version_spec):
        raise VersionError
    pack = importlib.import_module(package_name)
    return getattr(pack, class_desc.get('class'))


def get_link_list(source_path, work_path, requires_dist, entry):
    package_name = requires_dist.get('package_name')
    version_spec = requires_dist.get('version_spec')
    is_in_work = find_entry(work_path, package_name, version_spec)
    if is_in_work:
        return set()
    elif is_in_work is None:
        return None
    path = dir_opers.get_package_entry(source_path, entry)
    dependencies = dir_opers.get_metadata_ext(path)
    result = {entry}
    for require, pack in dependencies:
        res = get_link_list(source_path, work_path, require, pack)
        if res is None:
            return None
        result = result.union(res)
    return result


def find_entry(path, package_name, version_spec):
    for entry_path in dir_opers.get_work_package_entries(path):
        name, v, _ = dir_opers.get_metadata(entry_path)
        if name.lower().replace('-', '_') == package_name.lower().replace('-', '_'):
            if version.check_version(v, version_spec):
                return True
            else:
                pack_desc = f'Version {v} of package "{package_name}" in "{path}"'
                logging.warning(f'{pack_desc} does not meet the requirements "{version_spec}".')
                return None
    return False


def link_packages(source_path, work_path, packages):
        if packages is None:
            return False
        for package_name in packages:
            dir_opers.sync_link_package(f'{source_path}/{package_name}', work_path, shared_folders)
        return True

