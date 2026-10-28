import subprocess

def run_task(user_command):
    return subprocess.run(user_command, shell=True)
