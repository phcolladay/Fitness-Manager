import logging
import os
from typing import Optional

from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import strip_tags

from .email_service import EmailService

logger = logging.getLogger(__name__)


class SESEmailBackend(BaseEmailBackend):
    """
    Django email backend that delivers messages through AWS SESv2.
    """

    def __init__(self, fail_silently: bool = False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        max_retries = int(os.getenv("SES_MAX_RETRIES", "2"))
        retry_backoff = float(os.getenv("SES_RETRY_BACKOFF_SECONDS", "0.6"))
        self.service = EmailService(
            region=os.getenv("SES_REGION", "us-east-1"),
            from_email=os.getenv("SES_FROM_EMAIL", ""),
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff,
        )

    def open(self) -> bool:
        return True

    def close(self) -> None:
        return None

    @staticmethod
    def _extract_bodies(message) -> tuple[Optional[str], Optional[str]]:
        text_body = message.body if getattr(message, "content_subtype", "plain") == "plain" else None
        html_body = message.body if getattr(message, "content_subtype", "plain") == "html" else None

        for alt in getattr(message, "alternatives", []) or []:
            content = None
            mimetype = None
            if isinstance(alt, tuple) and len(alt) >= 2:
                content, mimetype = alt[0], alt[1]
            else:
                content = getattr(alt, "content", None)
                mimetype = getattr(alt, "mimetype", None)
            if mimetype == "text/html" and html_body is None:
                html_body = content
            elif mimetype == "text/plain" and text_body is None:
                text_body = content

        if not text_body and html_body:
            text_body = strip_tags(html_body)
        return text_body, html_body

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            to_addresses = list(message.to or [])
            if not to_addresses:
                continue

            text_body, html_body = self._extract_bodies(message)
            result = self.service.send_email(
                subject=message.subject or "",
                to_addresses=to_addresses,
                text_body=text_body,
                html_body=html_body,
                from_email=message.from_email,
                cc_addresses=list(message.cc or []),
                bcc_addresses=list(message.bcc or []),
                reply_to_addresses=list(message.reply_to or []),
            )

            if result.success:
                message.extra_headers = dict(getattr(message, "extra_headers", {}) or {})
                if result.message_id:
                    message.extra_headers["X-SES-Message-ID"] = result.message_id
                sent_count += 1
            else:
                logger.error(
                    "SES send failed subject=%s to=%s error=%s",
                    message.subject,
                    ",".join(to_addresses),
                    result.error,
                )
                if not self.fail_silently:
                    raise RuntimeError(result.error or "SES send failed")

        return sent_count
