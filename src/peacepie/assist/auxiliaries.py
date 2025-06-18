import sys


def is_testing():
    return "pytest" in sys.modules or "unittest" in sys.modules


def is_pycharm():
    return 'pycharm' in sys.executable.lower()