import logging
import shlex
import subprocess


def execute(cmd):
    if isinstance(cmd, str):
        cmd = ([cmd], 10)
    elif isinstance(cmd, list):
        cmd = (cmd, 10)
    timeout = cmd[1] if len(cmd) == 2 and isinstance(cmd[1], int) else 10
    processes = []
    for com in cmd[0]:
        args = shlex.split(com)
        logging.info(f'args="{str(args)}"')
        stdin = None if len(processes) == 0 else processes[-1].stdout
        processes.append(subprocess.Popen(args, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    stdout, stderr = processes[-1].communicate(timeout=timeout)
    return_code = processes[-1].returncode
    stdout_str = stdout.decode('utf-8').strip()
    stderr_str = stderr.decode('utf-8').strip()
    return return_code, stdout_str, stderr_str
