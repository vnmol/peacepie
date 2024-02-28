import shlex
import subprocess


def execute(cmd):
    timeout = 10
    if isinstance(cmd, tuple):
        args = shlex.split(cmd[0])
        timeout = cmd[1] if len(cmd) > 1 and isinstance(cmd[1], int) else 10
    else:
        args = shlex.split(cmd)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exe_out, exe_err = proc.communicate(timeout=timeout)
    exe_exitcode = proc.returncode
    return exe_exitcode, exe_out, exe_err
