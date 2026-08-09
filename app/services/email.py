from email.message import EmailMessage
from pathlib import Path
import smtplib
from email.utils import formataddr

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings


TEMPLATE_DIR = (
    Path(__file__).resolve().parents[1] / "templates"
)

jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(
        ["html", "xml"]
    ),
)


def render_template(
    template_name: str,
    **context,
) -> str:
    template = jinja_env.get_template(template_name)

    return template.render(**context)


def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    **context,
) -> None:

    if not settings.smtp_username:
        raise RuntimeError(
            "SMTP_USERNAME is not configured."
        )

    if not settings.smtp_password:
        raise RuntimeError(
            "SMTP_PASSWORD is not configured."
        )

    html_content = render_template(
        template_name,
        subject=subject,
        **context,
    )

    message = EmailMessage()

    message["Subject"] = subject

    message["From"] = formataddr(
        (
            settings.smtp_from_name,
            settings.smtp_from_email
            or settings.smtp_username,
        )
    )

    message["To"] = to_email

    message.set_content(
        "Please open this email in an HTML-compatible email client."
    )

    message.add_alternative(
        html_content,
        subtype="html",
    )

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=30,
    ) as smtp:

        smtp.starttls()

        smtp.login(
            settings.smtp_username,
            settings.smtp_password,
        )

        smtp.send_message(message)