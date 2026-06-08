import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_verification_email(to_email: str, token: str) -> None:
        html = f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
            <h2>¡Tu registro fue aprobado!</h2>
            <p>Ingresá a la app y completá tu registro usando el siguiente código:</p>
            <div style="font-size: 24px; font-weight: bold; letter-spacing: 4px;
                        padding: 16px; background: #f5f5f5; border-radius: 8px;
                        text-align: center; margin: 24px 0;">
                {token}
            </div>
            <p style="color: #888; font-size: 13px;">Este código es de un solo uso.</p>
        </div>
        """

        provider = settings.email_provider.lower().strip()

        if provider == "resend":
            from_addr = settings.email_from or "onboarding@resend.dev"
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {settings.email_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "from": from_addr,
                "to": [to_email],
                "subject": "Completá tu registro en el sistema de subastas",
                "html": html,
            }
            try:
                logger.info("Enviando email a %s via Resend API", to_email)
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                logger.info("Email enviado exitosamente a %s via Resend API", to_email)
            except httpx.HTTPStatusError as e:
                logger.error("Error de HTTP status de Resend API al enviar email a %s: %s - Response: %s", to_email, e, e.response.text)
                raise
            except httpx.RequestError as e:
                logger.error("Error de Red de Resend API al enviar email a %s: %s", to_email, e)
                raise
            except Exception as e:
                logger.error("Error inesperado al enviar email a %s via Resend: %s", to_email, e)
                raise

        elif provider == "sendgrid":
            from_addr = settings.email_from or "no-reply@yourdomain.com"
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {settings.email_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_addr},
                "subject": "Completá tu registro en el sistema de subastas",
                "content": [{"type": "text/html", "value": html}]
            }
            try:
                logger.info("Enviando email a %s via SendGrid API", to_email)
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                logger.info("Email enviado exitosamente a %s via SendGrid API", to_email)
            except httpx.HTTPStatusError as e:
                logger.error("Error de HTTP status de SendGrid API al enviar email a %s: %s - Response: %s", to_email, e, e.response.text)
                raise
            except httpx.RequestError as e:
                logger.error("Error de Red de SendGrid API al enviar email a %s: %s", to_email, e)
                raise
            except Exception as e:
                logger.error("Error inesperado al enviar email a %s via SendGrid: %s", to_email, e)
                raise

        else:
            # Fallback to SMTP
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Completá tu registro en el sistema de subastas"
            msg["From"] = settings.email_from or settings.smtp_user
            msg["To"] = to_email

            text = (
                f"Tu solicitud de registro fue aprobada.\n\n"
                f"Ingresá a la app y completá tu registro usando el siguiente código:\n\n"
                f"{token}\n\n"
                f"Este código es de un solo uso."
            )

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            try:
                logger.info("Enviando email a %s via %s:%s", to_email, settings.smtp_host, settings.smtp_port)
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(settings.email_from or settings.smtp_user, to_email, msg.as_string())
                logger.info("Email enviado exitosamente a %s", to_email)
            except smtplib.SMTPAuthenticationError as e:
                logger.error("Error de autenticacion SMTP (revisar SMTP_USER y SMTP_PASSWORD en .env): %s", e)
                raise
            except smtplib.SMTPException as e:
                logger.error("Error SMTP al enviar email a %s: %s", to_email, e)
                raise
            except Exception as e:
                logger.error("Error inesperado al enviar email a %s: %s", to_email, e)
                raise

