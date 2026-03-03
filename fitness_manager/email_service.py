import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 1


class EmailService:
    """
    SESv2 email sender with retry and structured result output.
    """

    def __init__(
        self,
        *,
        region: Optional[str] = None,
        from_email: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.6,
    ) -> None:
        self.region = region or os.getenv("SES_REGION", "us-east-1")
        self.from_email = from_email or os.getenv("SES_FROM_EMAIL", "")
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))

        access_key = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")

        client_kwargs = {"region_name": self.region}
        # In production, IAM Role credentials are preferred and auto-discovered by boto3.
        if access_key and secret_key:
            client_kwargs.update(
                {
                    "aws_access_key_id": access_key,
                    "aws_secret_access_key": secret_key,
                }
            )
        self._client = boto3.client("sesv2", **client_kwargs)

    def send_email(
        self,
        *,
        subject: str,
        to_addresses: list[str],
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        cc_addresses: Optional[list[str]] = None,
        bcc_addresses: Optional[list[str]] = None,
        reply_to_addresses: Optional[list[str]] = None,
    ) -> EmailSendResult:
        sender = (from_email or self.from_email or "").strip()
        if not sender:
            error = "Missing sender email. Set SES_FROM_EMAIL."
            logger.error("SES send failed: %s", error)
            return EmailSendResult(success=False, error=error)
        if not to_addresses:
            error = "Missing recipient list."
            logger.error("SES send failed: %s", error)
            return EmailSendResult(success=False, error=error)

        body: dict = {}
        if text_body:
            body["Text"] = {"Data": text_body, "Charset": "UTF-8"}
        if html_body:
            body["Html"] = {"Data": html_body, "Charset": "UTF-8"}
        if not body:
            body["Text"] = {"Data": "", "Charset": "UTF-8"}

        payload = {
            "FromEmailAddress": sender,
            "Destination": {
                "ToAddresses": to_addresses,
            },
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject or "", "Charset": "UTF-8"},
                    "Body": body,
                }
            },
        }
        if cc_addresses:
            payload["Destination"]["CcAddresses"] = cc_addresses
        if bcc_addresses:
            payload["Destination"]["BccAddresses"] = bcc_addresses
        if reply_to_addresses:
            payload["ReplyToAddresses"] = reply_to_addresses

        total_attempts = self.max_retries + 1
        for attempt in range(1, total_attempts + 1):
            try:
                response = self._client.send_email(**payload)
                message_id = response.get("MessageId")
                logger.info(
                    "SES email sent message_id=%s region=%s to=%s",
                    message_id,
                    self.region,
                    ",".join(to_addresses),
                )
                return EmailSendResult(success=True, message_id=message_id, attempts=attempt)
            except (ClientError, BotoCoreError) as exc:
                logger.exception(
                    "SES send failed attempt=%s/%s region=%s",
                    attempt,
                    total_attempts,
                    self.region,
                )
                if attempt < total_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                return EmailSendResult(
                    success=False,
                    error=str(exc),
                    attempts=attempt,
                )
