import structlog

from src.infrastructure.email.base import AbstractEmailProvider

logger = structlog.get_logger(__name__)


class ConsoleEmailProvider(AbstractEmailProvider):
    """Logs outbound mail instead of sending it.

    Default backend until SMTP/transactional-mail credentials are configured;
    lets the reset/verification flows work end-to-end in dev (token appears in
    the structured log).
    """

    async def send(self, to: str, subject: str, body: str) -> None:
        logger.info("email_send", to=to, subject=subject, body=body)
