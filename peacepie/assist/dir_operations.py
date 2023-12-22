import os
import shutil
import sys
from distutils.dir_util import copy_tree


def makedir(dirpath, clear=False):
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


def cleardir(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)


def copydir(orig, dest):
    copy_tree(orig, dest)


def adjust_path(path, process_name):
    pths = [pth for pth in sys.path]
    for pth in pths:
        if pth.startswith(path):
            sys.path.remove(pth)
    pth = f'{path}/work/{process_name}'
    makedir(pth, True)
    sys.path.append(pth)
