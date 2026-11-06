import asyncio
import ssl
import http.client
import urllib.parse
import time
import socket

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

async def check_port_and_banner(host, port, timeout=3.0):
    """
    Asynchronously checks if a TCP port is open and attempts 
    to grab HTTP/HTTPS banners and server headers.
    """
    open_status = False
    banner = {}
    
    # 1. TCP Connect Check
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        open_status = True
        writer.close()
        await writer.wait_closed()
    except Exception:
        return port, False, {}

    # 2. HTTP/HTTPS Banner Grabbing if port is open
    if open_status:
        try:
            use_ssl = (port in [443, 8443, 4443])
            def _sync_banner_fetch():
                conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=timeout) if use_ssl else http.client.HTTPConnection(host, port, timeout=timeout)
                conn.request("HEAD", "/")
                resp = conn.getresponse()
                headers = dict(resp.getheaders())
                conn.close()
                return resp.status, headers

            status, headers = await asyncio.to_thread(_sync_banner_fetch)
            banner = {
                "status_code": status,
                "server": headers.get("Server", "Unknown"),
                "powered_by": headers.get("X-Powered-By", "Unknown"),
                "headers": headers
            }
        except Exception as e:
            banner = {"error": str(e)}

    return port, open_status, banner

async def run_port_scanner(target_host, ports=None):
    """
    High-speed asynchronous port scanner and service profiler 
    designed for reconnaissance prior to red-team engine execution.
    """
    if ports is None:
        ports = [80, 443, 8080, 8443, 3000, 5000, 8888]

    try:
        resolved_ip = socket.gethostbyname(target_host)
        print(f"\n\033[96m[*] Scanner Target Resolved: {target_host} -> {resolved_ip}\033[0m")
    except socket.gaierror:
        print(f"\n\033[91m[!] Scanner Error: Could not resolve target '{target_host}'.\033[0m")
        return []

    start_time = time.time()
    print(f"\n\033[95m[***] ENGAGING ASYNCHRONOUS PORT PROFILER [{resolved_ip}] [***]\033[0m")
    
    tasks = [check_port_and_banner(resolved_ip, port) for port in ports]
    results = await asyncio.gather(*tasks)
    
    open_ports = []
    print(f"\n\033[36m[+] Scan Results for {target_host}:\033[0m")
    for port, is_open, banner in results:
        if is_open:
            print(f" \033[92m[OPEN] Port {port}/tcp | Server: {banner.get('server', 'N/A')} | Status: {banner.get('status_code', 'N/A')}\033[0m")
            open_ports.append({"port": port, "banner": banner})
        else:
            print(f" \033[90m[CLOSED] Port {port}/tcp\033[0m")

    duration = time.time() - start_time
    print(f"\n\033[33m[*] Reconnaissance complete in {duration:.2f}s. Active ports found: {len(open_ports)}\033[0m")
    return open_ports
