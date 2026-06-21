import unittest
from unittest.mock import patch, MagicMock
import httpx

from app.services.email_service import EmailService
from app.config import settings

class TestEmailService(unittest.TestCase):
    
    @patch("app.services.email_service.httpx.Client")
    @patch("app.services.email_service.settings")
    def test_send_verification_email_resend(self, mock_settings, mock_client_class):
        mock_settings.email_provider = "resend"
        mock_settings.email_api_key = "test_key"
        mock_settings.email_from = "onboarding@resend.dev"
        
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        
        EmailService.send_verification_email("target@example.com", "123456")
        
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_key")
        self.assertEqual(kwargs["json"]["to"], ["target@example.com"])
        self.assertEqual(kwargs["json"]["from"], "onboarding@resend.dev")
        self.assertIn("123456", kwargs["json"]["html"])

    @patch("app.services.email_service.httpx.Client")
    @patch("app.services.email_service.settings")
    def test_send_verification_email_sendgrid(self, mock_settings, mock_client_class):
        mock_settings.email_provider = "sendgrid"
        mock_settings.email_api_key = "test_key"
        mock_settings.email_from = "no-reply@example.com"
        
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        
        EmailService.send_verification_email("target@example.com", "123456")
        
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        self.assertEqual(args[0], "https://api.sendgrid.com/v3/mail/send")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_key")
        self.assertEqual(kwargs["json"]["personalizations"][0]["to"][0]["email"], "target@example.com")
        self.assertEqual(kwargs["json"]["from"]["email"], "no-reply@example.com")
        self.assertIn("123456", kwargs["json"]["content"][0]["value"])

    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    def test_send_verification_email_smtp(self, mock_settings, mock_smtp_class):
        mock_settings.email_provider = "smtp"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "password"
        mock_settings.email_from = "from@example.com"
        
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        EmailService.send_verification_email("target@example.com", "123456")
        
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "password")
        mock_smtp.sendmail.assert_called_once()
        args, kwargs = mock_smtp.sendmail.call_args
        self.assertEqual(args[0], "from@example.com")
        self.assertEqual(args[1], "target@example.com")

    @patch("app.services.email_service.httpx.Client")
    @patch("app.services.email_service.settings")
    def test_send_reset_password_email_resend(self, mock_settings, mock_client_class):
        mock_settings.email_provider = "resend"
        mock_settings.email_api_key = "test_key"
        mock_settings.email_from = "onboarding@resend.dev"
        
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        
        EmailService.send_reset_password_email("target@example.com", "654321")
        
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["json"]["to"], ["target@example.com"])
        self.assertIn("654321", kwargs["json"]["html"])
        self.assertEqual(kwargs["json"]["subject"], "Recuperación de contraseña")

    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    def test_send_reset_password_email_smtp(self, mock_settings, mock_smtp_class):
        mock_settings.email_provider = "smtp"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "password"
        mock_settings.email_from = "from@example.com"
        
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        EmailService.send_reset_password_email("target@example.com", "654321")
        
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "password")
        mock_smtp.sendmail.assert_called_once()
        args, kwargs = mock_smtp.sendmail.call_args
        self.assertEqual(args[0], "from@example.com")
        self.assertEqual(args[1], "target@example.com")

    @unittest.skipIf(not getattr(settings, "email_api_key", None), "No API key found, skipping integration test.")
    def test_integration_real_send(self):
        to_email = "tomaa.basualdo@gmail.com"
        print(f"\n[INTEGRATION TEST] sending real email to {to_email} via provider '{settings.email_provider}'...")
        try:
            EmailService.send_verification_email(to_email, "TEST-REAL-123456")
            print("[INTEGRATION TEST] Email sent successfully!")
        except Exception as e:
            self.fail(f"Real email sending failed: {e}")


class TestConfigValidation(unittest.TestCase):
    def test_valid_resend_config(self):
        from app.config import Settings
        cfg = Settings(
            database_url="postgresql://localhost",
            supabase_url="http://localhost",
            supabase_service_role_key="key",
            email_provider="resend",
            email_api_key="resend-api-key"
        )
        self.assertEqual(cfg.email_provider, "resend")

    def test_missing_api_key_for_resend(self):
        from app.config import Settings
        from pydantic import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            Settings(
                database_url="postgresql://localhost",
                supabase_url="http://localhost",
                supabase_service_role_key="key",
                email_provider="resend",
                email_api_key=None
            )
        self.assertIn("email_api_key is required", str(ctx.exception))

    def test_invalid_provider_fallback(self):
        from app.config import Settings
        cfg = Settings(
            database_url="postgresql://localhost",
            supabase_url="http://localhost",
            supabase_service_role_key="key",
            email_provider="invalid_provider",
            smtp_user="user",
            smtp_password="pwd"
        )
        self.assertEqual(cfg.email_provider, "smtp")

    def test_default_secret_allowed_in_development(self):
        from app.config import Settings
        cfg = Settings(
            database_url="postgresql://localhost",
            supabase_url="http://localhost",
            supabase_service_role_key="key",
            email_provider="sendgrid",
            email_api_key="sendgrid-api-key",
        )
        self.assertEqual(cfg.app_env, "development")

    def test_default_secret_rejected_in_production(self):
        from app.config import Settings
        from pydantic import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            Settings(
                app_env="production",
                database_url="postgresql://localhost",
                supabase_url="http://localhost",
                supabase_service_role_key="key",
                email_provider="sendgrid",
                email_api_key="sendgrid-api-key",
            )
        self.assertIn("secret_key must be set to a non-default value", str(ctx.exception))

    def test_custom_secret_allowed_in_production(self):
        from app.config import Settings
        cfg = Settings(
            app_env="production",
            database_url="postgresql://localhost",
            supabase_url="http://localhost",
            supabase_service_role_key="key",
            secret_key="a-long-random-secret-for-production-tests",
            email_provider="sendgrid",
            email_api_key="sendgrid-api-key",
        )
        self.assertEqual(cfg.app_env, "production")


