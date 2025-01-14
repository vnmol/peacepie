import logging
import os
import shutil
import sys


def recreatedir(dirpath):
    try:
        if os.path.exists(dirpath):
            shutil.rmtree(dirpath)
            logging.info(f'Old folder "{dirpath}" is deleted')
        os.makedirs(dirpath)
        logging.info(f'New folder "{dirpath}" is created')
        logging.info(f'Folder "{dirpath}" is {"" if len(os.listdir(dirpath)) == 0 else "not "}empty')
    except Exception as e:
        logging.exception(e)


def makedir(dirpath, clear=False):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    elif clear:
        cleardir(dirpath)


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


def copy_dir(orig, dest):
    try:
        shutil.copytree(orig, dest)
    except Exception as e:
        logging.exception(e)
    sync_directory(dest)
    logging.info(f'The directory "{orig}" is copied to "{dest}"')

def rem_dir(dest):
    if not os.path.exists(dest):
        return
    try:
        shutil.rmtree(dest)
    except Exception as e:
        logging.exception(e)


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


def adjust_path(path, process_name):
    pths = [pth for pth in sys.path]
    for pth in pths:
        if pth.startswith(path):
            sys.path.remove(pth)
    pth = f'{path}/work/{process_name}'
    makedir(pth, True)
    sys.path.append(pth)
    logging.info(f'SysPath "{pth}" is added')
