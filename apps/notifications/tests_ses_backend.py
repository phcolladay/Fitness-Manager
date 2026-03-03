from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase

from fitness_manager.email_backends import SESEmailBackend
from fitness_manager.email_service import EmailSendResult, EmailService


class EmailServiceTests(SimpleTestCase):
    @patch("fitness_manager.email_service.boto3.client")
    def test_send_email_returns_message_id(self, boto_client):
        fake_client = Mock()
        fake_client.send_email.return_value = {"MessageId": "ses-123"}
        boto_client.return_value = fake_client

        service = EmailService(region="us-east-1", from_email="notify@terrierfit.com")
        result = service.send_email(
            subject="Hello",
            to_addresses=["student@example.com"],
            text_body="text",
            html_body="<p>text</p>",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "ses-123")
        self.assertEqual(result.attempts, 1)

    @patch("fitness_manager.email_service.time.sleep", return_value=None)
    @patch("fitness_manager.email_service.boto3.client")
    def test_send_email_retries_once_then_succeeds(self, boto_client, _sleep):
        fake_client = Mock()
        fake_client.send_email.side_effect = [
            ClientError(
                error_response={"Error": {"Code": "ThrottlingException", "Message": "retry"}},
                operation_name="SendEmail",
            ),
            {"MessageId": "ses-456"},
        ]
        boto_client.return_value = fake_client

        service = EmailService(
            region="us-east-1",
            from_email="notify@terrierfit.com",
            max_retries=1,
            retry_backoff_seconds=0.0,
        )
        result = service.send_email(
            subject="Retry",
            to_addresses=["student@example.com"],
            text_body="body",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "ses-456")
        self.assertEqual(result.attempts, 2)


class SESEmailBackendTests(SimpleTestCase):
    @patch("fitness_manager.email_backends.EmailService.send_email")
    def test_backend_sends_html_and_text_and_sets_message_id_header(self, send_email):
        send_email.return_value = EmailSendResult(success=True, message_id="ses-789")
        backend = SESEmailBackend()

        message = EmailMultiAlternatives(
            subject="Subject",
            body="Plain text body",
            from_email="notify@terrierfit.com",
            to=["student@example.com"],
            connection=backend,
        )
        message.attach_alternative("<p>HTML body</p>", "text/html")

        count = backend.send_messages([message])

        self.assertEqual(count, 1)
        self.assertEqual(message.extra_headers.get("X-SES-Message-ID"), "ses-789")
        send_email.assert_called_once()
