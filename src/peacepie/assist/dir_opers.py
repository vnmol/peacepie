import asyncio
import logging
import os
import platform
import shutil
import sys
from pathlib import Path

from peacepie.assist import json_util, version


def recreatedir(dirpath):
    try:
        if os.path.exists(dirpath):
            shutil.rmtree(dirpath)
            logging.info(f'Old folder "{dirpath}" is deleted')
        os.makedirs(dirpath)
        logging.info(f'Folder "{dirpath}" is created')
        logging.info(f'Folder "{dirpath}" is {"" if len(os.listdir(dirpath)) == 0 else "not "}empty')
    except Exception as e:
        logging.exception(e)


def makedir(dirpath, clear=False):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
        logging.info(f'Folder "{dirpath}" is created')
    elif clear:
        cleardir(dirpath)
        logging.info(f'Folder "{dirpath}" is cleared')


def cleardir(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)


def do_dir(dirpath, clear=False):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    elif clear:
        clear_files(dirpath)


def clear_files(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
        elif os.path.isdir(filepath):
            clear_files(filepath)


def copy_dir(src, dst):
    try:
        shutil.copytree(src, dst)
    except Exception as e:
        logging.exception(e)
    sync_directory(dst)
    logging.info(f'The directory "{src}" is copied to "{dst}"')


def rem_dir(src):
    if not os.path.exists(src):
        return
    try:
        shutil.rmtree(src)
        logging.info(f'The directory "{src}" is deleted"')
    except Exception as e:
        logging.exception(e)


def move_dir(src, dst):
    try:
        shutil.move(src, dst)
        logging.info(f'The directory "{src}" is moved to "{dst}"')
    except Exception as e:
        logging.exception(e)

async def is_symlink_created(dest, timeout):
    step = 0.1
    total = 0.0
    while total < timeout:
        if os.path.islink(dest):
            return True
        total += step
        await asyncio.sleep(step)
    return False


async def create_symlink(orig, dest, timeout=1):
    try:
        os.symlink(os.path.abspath(orig), os.path.abspath(dest), target_is_directory=os.path.isdir(orig))
        res = await is_symlink_created(dest, timeout)
        logging.info(f'Symlink is created "{orig}" --> "{dest}"')
        return res
    except Exception as e:
        logging.exception(e)
    return False


def link_package(src, dst, shared_folders):
    for entry in os.listdir(src):
        if entry in shared_folders:
            for entrance in os.listdir(os.path.join(src, entry)):
                symlink = f'{dst}/{entry}/{entrance}'
                if not is_symlink_exist(symlink):
                    create_symlink(f'{src}/{entry}/{entrance}', symlink)
        else:
            create_symlink(os.path.join(src, entry), os.path.join(dst, entry))


def is_symlink_exist(path):
    try:
        res = os.path.islink(os.path.abspath(path))
        return res
    except Exception as e:
        logging.exception(e)
    return False


def is_dir_exist(path):
    pth = Path(path)
    return pth.exists() and pth.is_dir()


def copy_file(orig, dest):
    try:
        shutil.copy(orig, dest)
    except Exception as e:
        logging.exception(e)
    with open(dest, 'rb') as f:
        f.flush()
        os.fsync(f.fileno())
    logging.info(f'The file "{orig}" is copied to "{dest}"')


def sync_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                f.flush()
                os.fsync(f.fileno())


def compare_directories(dir1, dir2):
    def get_files_info(directory):
        files_info = {}
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    path = root[len(directory):] + '/' + file
                    files_info[path] = file_size
        return files_info

    return get_files_info(dir1) == get_files_info(dir2)


def adjust_path(path, process_name, shared_folders):
    pths = [pth for pth in sys.path]
    for pth in pths:
        if pth.startswith(path):
            sys.path.remove(pth)
    pth = f'{path}/work/{process_name}'
    makedir(pth, True)
    sys.path.append(pth)
    logging.info(f'SysPath "{pth}" is added')
    for folder in shared_folders:
        makedir(f'{pth}/{folder}')


def rename_dir(old_path, new_path):
    if not os.path.exists(old_path):
        return
    try:
        os.rename(old_path, new_path)
        logging.info(f'Folder "{old_path}" successfully renamed to "{new_path}"')
    except Exception as e:
        logging.exception(e)


def get_metadata(path):
    name = None
    ver = None
    dependencies = []
    try:
        with open(f'{path}/METADATA', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Name:'):
                    name = line.split(':', 1)[1].strip() # .replace('-', '_')
                elif line.startswith('Version:'):
                    ver = line.split(':', 1)[1].strip()
                elif line.startswith('Requires-Dist:'):
                    dependency = version.parse_requires_dist(line.split('Requires-Dist:')[1].strip())
                    if is_right_dependency(dependency):
                        dependencies.append(dependency)
        return name, ver, dependencies
    except Exception as e:
        logging.exception(e)


def is_right_dependency(dependency):
    if 'extra' in dependency:
        return False
    if not version.check_version(sys.version, dependency.get('python_version')):
        return False
    if dependency.get('platform_system') and platform.system() != dependency.get('platform_system'):
        return False
    return True

