import sys


def get_parameters():
    path = sys.argv[1]
    res = {}
    params = []
    try:
        with open(path) as f:
            params = [line.strip().split('#')[0] for line in f.readlines()]
    except BaseException as bex:
        print(bex)
    for param in params:
        if params == '':
            continue
        lst = param.strip().split('=', 1)
        if len(lst) == 2 and not lst[0].strip() == '' and not lst[1].strip() == '':
            res[lst[0].strip()] = lst[1].strip()
    return res
