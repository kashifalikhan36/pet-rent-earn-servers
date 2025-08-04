#!/usr/bin/env python3
"""
Email utility for password reset functionality
Adapted from the provided mass mailer code
"""

import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from jinja2 import Template
from core.config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class EmailService:
    def __init__(self):
        """Initialize the EmailService with configuration."""
        self.smtp_connection = None
        
    def connect_smtp(self) -> bool:
        """Establish SMTP connection."""
        try:
            # Close any existing connection first
            if self.smtp_connection:
                try:
                    self.smtp_connection.quit()
                except:
                    pass
                self.smtp_connection = None
            
            # Use SMTP_SSL for port 465, regular SMTP for other ports
            if settings.SMTP_PORT == 465:
                self.smtp_connection = smtplib.SMTP_SSL(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=30
                )
            else:
                self.smtp_connection = smtplib.SMTP(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=30
                )
                
                # Start TLS for security
                self.smtp_connection.starttls()
                
            self.smtp_connection.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            logger.info("Successfully connected to SMTP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            self.smtp_connection = None
            return False
            
    def is_connected(self) -> bool:
        """Check if SMTP connection is still active."""
        if not self.smtp_connection:
            return False
        try:
            # Test connection with NOOP command
            status = self.smtp_connection.noop()
            return status[0] == 250
        except:
            return False
            
    def ensure_connection(self) -> bool:
        """Ensure we have an active SMTP connection."""
        if not self.is_connected():
            logger.info("SMTP connection lost, reconnecting...")
            return self.connect_smtp()
        return True
            
    def disconnect_smtp(self):
        """Close SMTP connection."""
        if self.smtp_connection:
            try:
                self.smtp_connection.quit()
                logger.info("Disconnected from SMTP server")
            except:
                pass
            finally:
                self.smtp_connection = None
                
    def create_message(self, recipient_email: str, subject: str, html_body: str, 
                      text_body: str) -> MIMEMultipart:
        """Create email message with HTML and plain text alternatives."""
        msg = MIMEMultipart('alternative')
        msg['From'] = settings.FROM_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Attach text and HTML parts
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(html_body, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
                    
        return msg
        
    def send_email(self, recipient_email: str, subject: str, html_body: str, 
                  text_body: str) -> bool:
        """Send email with automatic reconnection."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Ensure we have a valid connection before sending
                if not self.ensure_connection():
                    logger.error(f"Could not establish SMTP connection for {recipient_email}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying email to {recipient_email} (attempt {attempt + 2})")
                        continue
                    else:
                        return False
                
                # Create message
                msg = self.create_message(recipient_email, subject, html_body, text_body)
                
                # Send email
                self.smtp_connection.send_message(msg)
                
                logger.info(f"Email sent successfully to {recipient_email}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying email to {recipient_email} (attempt {attempt + 2})")
                    # Force reconnection on next attempt
                    self.smtp_connection = None
                else:
                    logger.error(f"Could not send email to {recipient_email} after {max_retries} attempts")
                    return False
        
        return False
            
    def send_password_reset_email(self, user_email: str, user_name: str, 
                                 reset_token: str) -> bool:
        """Send password reset email to user."""
        try:
            # Create reset URL
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            
            # Email context
            context = {
                'user_name': user_name,
                'reset_url': reset_url,
                'support_email': settings.FROM_EMAIL,
                'current_year': datetime.now().year
            }
            
            # Email templates
            html_template = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Password Reset Request</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #007bff; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background: #f8f9fa; }
                    .button { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 20px 0; }
                    .footer { text-align: center; color: #666; font-size: 12px; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <p>Hello {{ user_name }},</p>
                        <p>We received a request to reset your password for your HumanText AI account.</p>
                        <p>If you made this request, please click the button below to reset your password:</p>
                        <p><a href="{{ reset_url }}" class="button">Reset Password</a></p>
                        <p>Or copy and paste this link into your browser:</p>
                        <p><a href="{{ reset_url }}">{{ reset_url }}</a></p>
                        <p><strong>This link will expire in 24 hours.</strong></p>
                        <p>If you didn't request this password reset, please ignore this email or contact support at {{ support_email }}.</p>
                        <p>Best regards,<br>The HumanText AI Team</p>
                    </div>
                    <div class="footer">
                        <p>&copy; {{ current_year }} HumanText AI. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """)
            
            text_template = Template("""
            Password Reset Request
            
            Hello {{ user_name }},
            
            We received a request to reset your password for your HumanText AI account.
            
            If you made this request, please click the link below to reset your password:
            {{ reset_url }}
            
            This link will expire in 24 hours.
            
            If you didn't request this password reset, please ignore this email or contact support at {{ support_email }}.
            
            Best regards,
            The HumanText AI Team
            
            © {{ current_year }} HumanText AI. All rights reserved.
            """)
            
            # Render templates
            html_body = html_template.render(**context)
            text_body = text_template.render(**context)
            
            # Send email
            return self.send_email(
                recipient_email=user_email,
                subject="Password Reset Request - HumanText AI",
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False
        finally:
            self.disconnect_smtp()


# Global email service instance
email_service = EmailService() 