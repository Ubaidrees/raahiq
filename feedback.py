import smtplib
from email.mime.text import MIMEText
from datetime import datetime


def send_feedback_email(feedback_text, contact_email, gmail_address, gmail_app_password):
    """
    Sends a feedback email straight to the developer's own Gmail inbox using
    Gmail's SMTP server. Requires a Gmail "App Password" (NOT the normal
    account password) — set up via:
    Google Account > Security > 2-Step Verification > App passwords.

    Raises an exception on failure so the caller can show an error message;
    does not silently swallow errors since feedback delivery matters.
    """
    if not gmail_address or not gmail_app_password:
        raise ValueError("Gmail credentials are not configured (GMAIL_ADDRESS / GMAIL_APP_PASSWORD missing).")

    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
    body_lines = [
        f"New feedback received on RaahIQ — {timestamp}",
        "",
        feedback_text.strip(),
    ]
    if contact_email:
        body_lines += ["", f"User's contact email (if they want a reply): {contact_email}"]

    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = "🚌 New RaahIQ Feedback"
    msg["From"] = gmail_address
    msg["To"] = gmail_address
    if contact_email:
        msg["Reply-To"] = contact_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [gmail_address], msg.as_string())