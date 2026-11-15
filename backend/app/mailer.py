"""SMTP transport. Tokens and recipient addresses must never be logged."""
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import parseaddr
from urllib.parse import urlencode, urlsplit


class MailConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    sender: str
    security: str
    username: str
    password: str
    public_url: str

    @classmethod
    def load(cls):
        host = os.getenv("SMTP_HOST", "").strip()
        sender = os.getenv("SMTP_FROM", "").strip()
        security = os.getenv("SMTP_SECURITY", "starttls")
        public_url = os.getenv("APP_PUBLIC_URL", "").rstrip("/")
        username = os.getenv("SMTP_USERNAME", "")
        password = os.getenv("SMTP_PASSWORD", "")
        try:
            port = int(os.getenv("SMTP_PORT", "465" if security == "ssl" else "587"))
            url = urlsplit(public_url)
            valid_url = (
                bool(url.hostname) and not url.username and not url.password and not url.query and not url.fragment
                and (url.scheme == "https" or (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}))
            )
        except ValueError:
            raise MailConfigurationError("Invalid email configuration") from None
        if (
            not host or not sender or "@" not in parseaddr(sender)[1] or not 1 <= port <= 65535
            or security not in {"starttls", "ssl", "plain"} or not valid_url
            or any(c in host + sender + public_url for c in "\r\n") or (bool(username) != bool(password))
        ):
            raise MailConfigurationError("Invalid email configuration")
        return cls(host, port, sender, security, username, password, public_url)


def send_account_email(settings: MailSettings, recipient: str, purpose: str, token: str, action_id: str) -> None:
    reset = purpose == "reset_password"
    page = "reset-password" if reset else "verify-email"
    link = f"{settings.public_url}/{page}#{urlencode({'token': token})}"
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = recipient
    message["Subject"] = "WordSpeak: Reset your password" if reset else "WordSpeak: Verify your email"
    message["Message-ID"] = f"<{action_id}@{parseaddr(settings.sender)[1].split('@')[-1]}>"
    expires = "30 minutes" if reset else "24 hours"
    message.set_content(
        f"Open this link to {'reset your password' if reset else 'verify your email'}:\n\n{link}\n\n"
        f"This link expires in {expires} and can be used once. "
        "If you did not request this email, you can ignore it.\n"
    )
    context = ssl.create_default_context()
    connection = (
        smtplib.SMTP_SSL(settings.host, settings.port, timeout=10, context=context)
        if settings.security == "ssl" else smtplib.SMTP(settings.host, settings.port, timeout=10)
    )
    with connection as smtp:
        if settings.security == "starttls":
            smtp.starttls(context=context)
        if settings.username:
            smtp.login(settings.username, settings.password)
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
