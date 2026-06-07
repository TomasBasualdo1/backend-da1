import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


class EmailService:
    @staticmethod
    def send_verification_email(to_email: str, token: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Completá tu registro en el sistema de subastas"
        msg["From"] = settings.smtp_user
        msg["To"] = to_email

        text = (
            f"Tu solicitud de registro fue aprobada.\n\n"
            f"Ingresá a la app y completá tu registro usando el siguiente código:\n\n"
            f"{token}\n\n"
            f"Este código es de un solo uso."
        )
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

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to_email, msg.as_string())
