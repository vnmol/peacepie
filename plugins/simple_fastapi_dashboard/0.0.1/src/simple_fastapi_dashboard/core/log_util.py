import re

pattern = r"'password':\s*(['\"])(.*?)(\1)"


def format_msg(msg):
    res = str(msg)
    return re.sub(pattern, r"'password': '******'", res)
