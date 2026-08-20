"""
Email Service for Liara
Handles password reset emails and other notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "Liara AI Assistant")
        
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.smtp_user and self.smtp_password)
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email service not configured. Check SMTP environment variables.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            # Add text part (fallback)
            if text_body:
                part1 = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(part1)
            
            # Add HTML part
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part2)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        personalized_message: str,
        reset_url: Optional[str] = None
    ) -> bool:
        """
        Send password reset email with personalized message from Liara
        
        Args:
            to_email: User's email
            username: Username
            reset_token: Reset token
            personalized_message: Personalized message from Liara based on memories
            reset_url: Optional custom reset URL (defaults to frontend URL)
            
        Returns:
            True if sent successfully
        """
        if not reset_url:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        
        subject = f"🔑 Passwort-Reset für deinen Liara-Account"
        
        # HTML Email Template
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 20px;
        }}
        .personal-message {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-style: italic;
            border-left: 4px solid rgba(255,255,255,0.5);
        }}
        .personal-message p {{
            margin: 0;
            line-height: 1.8;
        }}
        .button {{
            display: inline-block;
            padding: 14px 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .button:hover {{
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}
        .token-box {{
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
            font-family: 'Courier New', monospace;
            word-break: break-all;
            font-size: 13px;
            color: #495057;
        }}
        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.8);
            font-size: 13px;
            margin-top: 20px;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
            color: #856404;
        }}
        .signature {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
            color: #6c757d;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Liara AI Assistant</h1>
            <p>Dein persönlicher KI-Begleiter</p>
        </div>
        
        <div class="content">
            <h2>Hallo {username}! 👋</h2>
            
            <p>Dein Administrator hat ein neues Passwort für deinen Liara-Account generiert.</p>
            
            <div class="personal-message">
                <p><strong>💭 Persönliche Nachricht von Liara:</strong></p>
                <p>{personalized_message}</p>
            </div>
            
            <p>Klicke auf den Button unten, um ein neues Passwort zu setzen:</p>
            
            <div style="text-align: center;">
                <a href="{reset_url}" class="button">
                    🔐 Neues Passwort setzen
                </a>
            </div>
            
            <div class="warning">
                <strong>⏰ Wichtig:</strong> Dieser Link ist 24 Stunden gültig.
            </div>
            
            <p><strong>Oder verwende diesen Token manuell:</strong></p>
            <div class="token-box">
                {reset_token}
            </div>
            
            <div class="signature">
                <p>Mit freundlichen Grüßen,<br>
                <strong>Liara</strong> 💜<br>
                <em>Deine KI-Assistentin mit Erinnerungsvermögen</em></p>
            </div>
        </div>
        
        <div class="footer">
            <p>Diese E-Mail wurde automatisch von Liara generiert.<br>
            Falls du diese E-Mail nicht erwartet hast, ignoriere sie bitte.</p>
            <p style="margin-top: 10px; font-size: 11px;">
                Liara AI Assistant · Privacy-First · Self-Hosted
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text fallback
        text_body = f"""
Hallo {username}!

Dein Administrator hat ein neues Passwort für deinen Liara-Account generiert.

--- Persönliche Nachricht von Liara ---
{personalized_message}
---

Setze hier dein neues Passwort:
{reset_url}

Oder verwende diesen Token manuell:
{reset_token}

WICHTIG: Dieser Link ist 24 Stunden gültig.

Mit freundlichen Grüßen,
Liara - Deine KI-Assistentin

---
Falls du diese E-Mail nicht erwartet hast, ignoriere sie bitte.
"""
        
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )


# Singleton instance
email_service = EmailService()
