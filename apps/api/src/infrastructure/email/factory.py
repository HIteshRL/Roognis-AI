from src.config import get_settings
from src.infrastructure.email.base import AbstractEmailProvider
from src.infrastructure.email.console_provider import ConsoleEmailProvider
from src.infrastructure.email.smtp_provider import SmtpEmailProvider


def get_email_provider() -> AbstractEmailProvider:
    settings = get_settings()
    if settings.email_provider == "smtp":
        return SmtpEmailProvider(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            sender=settings.smtp_sender,
            use_tls=settings.smtp_use_tls,
        )
    return ConsoleEmailProvider()
