import sys


def get_parameters():
    res = {}
    params = []
    try:
        path = sys.argv[1]
        with open(path) as f:
            params = [line.strip().split('#')[0] for line in f.readlines()]
    except BaseException as bex:
        print(bex)
    for param in params:
        if params == '':
            continue
        lst = param.strip().split('=', 1)
        if len(lst) == 2 and not lst[0].strip() == '' and not lst[1].strip() == '':
            name = lst[0].strip()
            value = lst[1].strip()
            if name == 'developing_mode':
                value = value == 'True'
            elif name == 'inter_port':
                value = int(value)
            elif name == 'intra_port':
                value = int(value)
            res[name] = value
    return res
