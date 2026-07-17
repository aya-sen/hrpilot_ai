import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple


def _get_smtp_config(city: str) -> Tuple[str, int, str, str, str]:
    """Return (host, port, username, password, from_email) for given city."""
    key = (city or "").strip().upper()
    prefix = f"SMTP_{key}_"  # e.g. SMTP_CASABLANCA_

    host = os.getenv(prefix + "HOST")
    port = os.getenv(prefix + "PORT")
    username = os.getenv(prefix + "USER")
    password = os.getenv(prefix + "PASS")
    from_email = os.getenv(prefix + "FROM")

    if not host or not port or not username or not password or not from_email:
        raise ValueError(
            f"Missing SMTP env vars for city={city}. Expected: {prefix}HOST/PORT/USER/PASS/FROM"
        )

    return host, int(port), username, password, from_email


def send_temp_password_email(*, to_email: str, to_name: str, city: str, temp_password: str) -> None:
    """Send a one-time temp password in plain text (as required by the workflow)."""
    host, port, username, password, from_email = _get_smtp_config(city)

    subject = f"Votre mot de passe temporaire (HRPilot AI) - {city}"
    html_body = f"""
    <html><body>
    <p>Bonjour <b>{to_name}</b>,</p>
    <p>Votre mot de passe temporaire est :</p>
    <p style="font-size:18px; font-weight:bold;">{temp_password}</p>
    <p>Vous devrez le modifier lors de votre première connexion.</p>
    <p>Cordialement,<br/>HRPilot AI</p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, [to_email], msg.as_string())

