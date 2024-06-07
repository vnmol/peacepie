import logging
import os
import shutil
import sys
import time


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


def copydir(orig, dest):
    try:
        shutil.copytree(orig, dest)
        for _ in range(3):
            if compare_directories(orig, dest):
                break
            time.sleep(1)
    except Exception as e:
        logging.exception(e)


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
