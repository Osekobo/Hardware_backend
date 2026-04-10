import africastalking
import smtplib
from email.mime.text import MIMEText


def send_email(to_email: str, subject: str, message: str):
    sender = "your_email@gmail.com"
    password = "your_app_password"

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    server.quit()


africastalking.initialize(
    username="sandbox",
    api_key="your_api_key"
)

sms = africastalking.SMS


def send_sms(phone: str, message: str):
    sms.send(message, [phone])
