import shlex
import subprocess


def execute(cmd):
    args = shlex.split(cmd)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exe_out, exe_err = proc.communicate()
    exe_exitcode = proc.returncode
    return exe_exitcode, exe_out, exe_err
