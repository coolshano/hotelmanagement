import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str | None = None,
) -> None:
    message = EmailMessage()

    message["From"] = (
        f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    )
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(
        text
        or "Please view this email in an HTML-compatible email client."
    )

    message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=20,
        ) as smtp:
            smtp.starttls()

            smtp.login(
                settings.smtp_username,
                settings.smtp_password,
            )

            response = smtp.send_message(message)

            print("SMTP RESPONSE:", response)

        logger.info("Email sent successfully to %s", to_email)

    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        raise


def send_welcome_email(user) -> None:
    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: auto; padding: 30px;">

        <h2 style="color: #8B6F47;">
            Welcome to Royal Crest Hotel
        </h2>

        <p>Dear {user.full_name},</p>

        <p>
            Welcome to Royal Crest Hotel.
            Your account has been successfully created.
        </p>

        <p>
            You can now sign in and manage your bookings through
            our hotel management system.
        </p>

        <p>
            We look forward to welcoming you.
        </p>

        <p>
            Kind regards,<br>
            <strong>Royal Crest Hotel</strong>
        </p>

    </div>
</body>
</html>
"""

    text = f"""
Dear {user.full_name},

Welcome to Royal Crest Hotel.

Your account has been successfully created.

You can now sign in and manage your bookings through our hotel
management system.

We look forward to welcoming you.

Kind regards,
Royal Crest Hotel
"""

    send_email(
        to_email=user.email,
        subject="Welcome to Royal Crest Hotel",
        html=html,
        text=text,
    )


def send_booking_confirmation_email(booking) -> None:
    user = booking.user
    room = booking.room

    room_number = room.room_number if room else "N/A"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: auto; padding: 30px;">

        <h2 style="color: #8B6F47;">
            Booking Confirmed
        </h2>

        <p>Dear {user.full_name},</p>

        <p>
            Thank you for choosing <strong>Royal Crest Hotel</strong>.
            Your booking has been successfully confirmed.
        </p>

        <div style="
            background: #f7f4ef;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        ">

            <h3>Booking Details</h3>

            <p>
                <strong>Booking Reference:</strong>
                {booking.reference}
            </p>

            <p>
                <strong>Room:</strong>
                {room_number}
            </p>

            <p>
                <strong>Check-in:</strong>
                {booking.check_in}
            </p>

            <p>
                <strong>Check-out:</strong>
                {booking.check_out}
            </p>

            <p>
                <strong>Guests:</strong>
                {booking.guests}
            </p>

            <p>
                <strong>Nights:</strong>
                {booking.nights}
            </p>

            <p>
                <strong>Total:</strong>
                {booking.currency} {booking.total_price}
            </p>

            <p>
                <strong>Status:</strong>
                {booking.status}
            </p>

        </div>

        <p>
            We look forward to welcoming you to Royal Crest Hotel.
        </p>

        <p>
            Kind regards,<br>
            <strong>Royal Crest Hotel</strong>
        </p>

    </div>
</body>
</html>
"""

    text = f"""
Dear {user.full_name},

Thank you for choosing Royal Crest Hotel.

Your booking has been successfully confirmed.

BOOKING DETAILS

Booking Reference: {booking.reference}
Room: {room_number}
Check-in: {booking.check_in}
Check-out: {booking.check_out}
Guests: {booking.guests}
Nights: {booking.nights}
Total: {booking.currency} {booking.total_price}
Status: {booking.status}

We look forward to welcoming you to Royal Crest Hotel.

Kind regards,
Royal Crest Hotel
"""

    send_email(
        to_email=user.email,
        subject=f"Booking Confirmation - {booking.reference}",
        html=html,
        text=text,
    )

