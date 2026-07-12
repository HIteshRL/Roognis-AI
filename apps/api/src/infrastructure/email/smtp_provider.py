import asyncio
import smtplib
from email.mime.text import MIMEText

import structlog

from src.infrastructure.email.base import AbstractEmailProvider

logger = structlog.get_logger(__name__)


class SmtpEmailProvider(AbstractEmailProvider):
    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        sender: str,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls

    async def send(self, to: str, subject: str, body: str) -> None:
        # smtplib is blocking; run in a worker thread to keep the loop free.
        await asyncio.to_thread(self._send_sync, to, subject, body)

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._sender
        msg["To"] = to
        with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.sendmail(self._sender, [to], msg.as_string())
        logger.info("email_sent", to=to, subject=subject)
