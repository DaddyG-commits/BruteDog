import asyncio
import ssl
import http.client
import time
import socket
import sys

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

DEFAULT_PORTS = [
    21, 22, 25, 53, 80, 110, 143, 443, 445, 993, 995,
    1433, 1521, 3306, 3389, 5432, 5900, 6379, 8000, 8080,
    8443, 8888, 27017, 3000, 5000, 9000, 9200, 11211,
]


async def check_port_and_banner(host, port, timeout=2.5):
    open_status = False
    banner = {}
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        open_status = True
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    except Exception:
        return port, False, {}

    if open_status and port in (80, 443, 8080, 8443, 3000, 5000, 8000, 8888):
        try:
            use_ssl = port in (443, 8443)

            def _sync():
                conn = (
                    http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=timeout)
                    if use_ssl
                    else http.client.HTTPConnection(host, port, timeout=timeout)
                )
                conn.request("HEAD", "/", headers={"Host": host, "User-Agent": "BruteDog-Recon"})
                resp = conn.getresponse()
                headers = dict(resp.getheaders())
                status = resp.status
                conn.close()
                return status, headers

            status, headers = await asyncio.to_thread(_sync)
            banner = {
                "status_code": status,
                "server": headers.get("Server", "Unknown"),
                "powered_by": headers.get("X-Powered-By", "Unknown"),
                "headers": headers,
            }
        except Exception as e:
            banner = {"error": str(e)}
    return port, open_status, banner


async def run_port_scanner(target_host, ports=None):
    if ports is None:
        ports = DEFAULT_PORTS
    try:
        resolved_ip = socket.gethostbyname(target_host)
        sys.stdout.write(f"\n\033[96m[*] Scanner: {target_host} → {resolved_ip}\033[0m\n")
        sys.stdout.flush()
    except socket.gaierror:
        sys.stdout.write(f"\n\033[91m[!] Cannot resolve {target_host}\033[0m\n")
        return []

    start = time.time()
    sys.stdout.write(f"\033[95m[***] PORT PROFILER ({len(ports)} ports) [***]\033[0m\n")
    sys.stdout.flush()

    # Scan by IP for TCP; HTTP banner uses Host header with domain when possible
    tasks = [check_port_and_banner(resolved_ip, port) for port in ports]
    results = await asyncio.gather(*tasks)

    open_ports = []
    for port, is_open, banner in results:
        if is_open:
            sys.stdout.write(
                f" \033[92m[OPEN] {port}/tcp | Server={banner.get('server', 'n/a')} | HTTP={banner.get('status_code', 'n/a')}\033[0m\n"
            )
            sys.stdout.flush()
            open_ports.append({"port": port, "banner": banner})

    sys.stdout.write(f"\n\033[33m[*] Recon done in {time.time()-start:.2f}s | open={len(open_ports)}\033[0m\n")
    sys.stdout.flush()
    return open_ports
