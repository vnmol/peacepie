import inspect
import sys
from datetime import datetime


def is_testing():
    return "pytest" in sys.modules or "unittest" in sys.modules


def is_pycharm():
    return 'pycharm' in sys.executable.lower()


def get_current_time_string():
    now = datetime.now()
    return now.strftime('%H:%M:%S.%f')


def get_primary_class(module):
    classes = inspect.getmembers(module, inspect.isclass)
    if classes:
        primary_class_name, primary_class = classes[0]
        return primary_class
    else:
        return None
