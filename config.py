# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Email settings (using Gmail as example)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
    
    # For production, consider using:
    # - SendGrid
    # - Mailgun
    # - Amazon SES
    # - Resend

settings = Settings()