# utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings
import logging

logger = logging.getLogger(__name__)

def send_reset_email(to_email: str, otp: str):
    """Send password reset email with OTP"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = "Password Reset Request - Kione Hardware"
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #E04E00; padding: 20px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ padding: 30px; background-color: #f9f9f9; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #E04E00; text-align: center; 
                             padding: 20px; letter-spacing: 5px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #E04E00; 
                          color: white; text-decoration: none; border-radius: 4px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Kione Hardware</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>We received a request to reset your password. Use the code below to reset it:</p>
                    <div class="otp-code">{otp}</div>
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <hr>
                    <p style="font-size: 14px;">For security, never share this code with anyone.</p>
                </div>
                <div class="footer">
                    <p>Kione Hardware & General Stores<br>Migori, Kenya</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_body = f"""
        Password Reset Request
        
        You requested to reset your password. Use this code: {otp}
        
        This code expires in 10 minutes.
        
        If you didn't request this, please ignore this email.
        
        ---
        Kione Hardware & General Stores
        Migori, Kenya
        """
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Reset email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False