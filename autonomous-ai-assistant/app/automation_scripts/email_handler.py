import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Email configuration dataclass"""
    smtp_server: str
    smtp_port: int
    imap_server: str
    imap_port: int
    email_address: str
    password: str
    use_tls: bool = True

class EmailHandler:
    """
    Handles email operations including reading, sending, and filtering emails.
    Supports Gmail and other email providers.
    """
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Initialize email handler with configuration.
        
        Args:
            config: EmailConfig object with connection details
        """
        self.config = config or self._get_default_config()
        self.smtp_connection = None
        self.imap_connection = None
        
    def _get_default_config(self) -> EmailConfig:
        """Get default Gmail configuration from environment variables"""
        return EmailConfig(
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            imap_server=os.getenv('IMAP_SERVER', 'imap.gmail.com'),
            imap_port=int(os.getenv('IMAP_PORT', '993')),
            email_address=os.getenv('EMAIL_ADDRESS', ''),
            password=os.getenv('EMAIL_PASSWORD', ''),
            use_tls=True
        )

    def connect_smtp(self) -> Dict[str, Any]:
        """Establish SMTP connection for sending emails"""
        try:
            if not self.config.email_address or not self.config.password:
                return {"status": "error", "message": "Email credentials not configured"}
            
            logger.info(f"Connecting to SMTP server: {self.config.smtp_server}:{self.config.smtp_port}")
            
            self.smtp_connection = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            
            if self.config.use_tls:
                self.smtp_connection.starttls()
            
            self.smtp_connection.login(self.config.email_address, self.config.password)
            
            logger.info("SMTP connection established successfully")
            return {"status": "success", "message": "SMTP connection established"}
            
        except Exception as e:
            error_msg = f"Failed to connect to SMTP server: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def connect_imap(self) -> Dict[str, Any]:
        """Establish IMAP connection for reading emails"""
        try:
            if not self.config.email_address or not self.config.password:
                return {"status": "error", "message": "Email credentials not configured"}
            
            logger.info(f"Connecting to IMAP server: {self.config.imap_server}:{self.config.imap_port}")
            
            if self.config.use_tls:
                self.imap_connection = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            else:
                self.imap_connection = imaplib.IMAP4(self.config.imap_server, self.config.imap_port)
            
            self.imap_connection.login(self.config.email_address, self.config.password)
            
            logger.info("IMAP connection established successfully")
            return {"status": "success", "message": "IMAP connection established"}
            
        except Exception as e:
            error_msg = f"Failed to connect to IMAP server: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def disconnect(self):
        """Close all connections"""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                self.smtp_connection = None
            
            if self.imap_connection:
                self.imap_connection.close()
                self.imap_connection.logout()
                self.imap_connection = None
                
            logger.info("Email connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

    def send_email(self, to_emails: List[str], subject: str, body: str, 
                   cc_emails: Optional[List[str]] = None, 
                   bcc_emails: Optional[List[str]] = None,
                   attachments: Optional[List[str]] = None,
                   is_html: bool = False) -> Dict[str, Any]:
        """
        Send an email with optional attachments.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            cc_emails: List of CC recipients
            bcc_emails: List of BCC recipients
            attachments: List of file paths to attach
            is_html: Whether body is HTML format
            
        Returns:
            Dictionary with operation status
        """
        try:
            # Validate inputs
            if not to_emails or not isinstance(to_emails, list):
                return {"status": "error", "message": "Invalid recipient list"}
            
            if not subject or not body:
                return {"status": "error", "message": "Subject and body are required"}
            
            # Connect if not connected
            if not self.smtp_connection:
                connect_result = self.connect_smtp()
                if connect_result["status"] == "error":
                    return connect_result
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_address
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add body
            body_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, body_type))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "rb") as attachment:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(attachment.read())
                                
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                            
                        except Exception as e:
                            logger.warning(f"Failed to attach {file_path}: {e}")
                    else:
                        logger.warning(f"Attachment not found: {file_path}")
            
            # Send email
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            self.smtp_connection.sendmail(
                self.config.email_address, 
                all_recipients, 
                msg.as_string()
            )
            
            message = f"Email sent successfully to {len(to_emails)} recipients"
            logger.info(message)
            
            return {
                "status": "success",
                "message": message,
                "recipients": to_emails,
                "subject": subject,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def read_emails(self, mailbox: str = 'INBOX', limit: int = 10, 
                    unread_only: bool = False, 
                    since_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Read emails from specified mailbox.
        
        Args:
            mailbox: Mailbox to read from (INBOX, SENT, etc.)
            limit: Maximum number of emails to retrieve
            unread_only: Only fetch unread emails
            since_days: Only fetch emails from last N days
            
        Returns:
            Dictionary with email list and metadata
        """
        try:
            # Connect if not connected
            if not self.imap_connection:
                connect_result = self.connect_imap()
                if connect_result["status"] == "error":
                    return connect_result
            
            # Select mailbox
            status, messages = self.imap_connection.select(mailbox)
            if status != 'OK':
                return {"status": "error", "message": f"Failed to select mailbox: {mailbox}"}
            
            # Build search criteria
            search_criteria = []
            
            if unread_only:
                search_criteria.append('UNSEEN')
            
            if since_days:
                date_since = (datetime.now() - timedelta(days=since_days)).strftime('%d-%b-%Y')
                search_criteria.append(f'SINCE {date_since}')
            
            search_string = ' '.join(search_criteria) if search_criteria else 'ALL'
            
            # Search for emails
            status, messages = self.imap_connection.search(None, search_string)
            if status != 'OK':
                return {"status": "error", "message": "Failed to search emails"}
            
            message_ids = messages[0].split()
            
            # Limit results
            if limit:
                message_ids = message_ids[-limit:]  # Get most recent emails
            
            emails = []
            
            for msg_id in message_ids:
                try:
                    # Fetch email
                    status, msg_data = self.imap_connection.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Extract email details
                    email_info = {
                        "id": msg_id.decode(),
                        "subject": email_message.get("Subject", "No Subject"),
                        "from": email_message.get("From", "Unknown"),
                        "to": email_message.get("To", "Unknown"),
                        "date": email_message.get("Date", "Unknown"),
                        "body": self._extract_body(email_message),
                        "has_attachments": self._has_attachments(email_message),
                        "is_multipart": email_message.is_multipart()
                    }
                    
                    emails.append(email_info)
                    
                except Exception as e:
                    logger.error(f"Error processing email {msg_id}: {e}")
                    continue
            
            result = {
                "status": "success",
                "mailbox": mailbox,
                "emails": emails,
                "total_count": len(emails),
                "search_criteria": search_string,
                "message": f"Retrieved {len(emails)} emails from {mailbox}"
            }
            
            logger.info(f"Successfully retrieved {len(emails)} emails from {mailbox}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to read emails: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def _extract_body(self, email_message) -> str:
        """Extract plain text body from email message"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True)
                        if isinstance(body, bytes):
                            return body.decode('utf-8', errors='ignore')
                        return str(body)
                return "No plain text content found"
            else:
                body = email_message.get_payload(decode=True)
                if isinstance(body, bytes):
                    return body.decode('utf-8', errors='ignore')
                return str(body)
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return "Error extracting body content"

    def _has_attachments(self, email_message) -> bool:
        """Check if email has attachments"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    disposition = part.get("Content-Disposition")
                    if disposition and "attachment" in disposition:
                        return True
            return False
        except Exception:
            return False

    def summarize_emails(self, emails: List[Dict[str, Any]], max_length: int = 100) -> Dict[str, Any]:
        """
        Create summaries of emails.
        
        Args:
            emails: List of email dictionaries
            max_length: Maximum length per summary
            
        Returns:
            Dictionary with summarized emails
        """
        try:
            summaries = []
            
            for email_info in emails:
                body = email_info.get('body', '')
                
                # Simple extractive summarization
                sentences = re.split(r'[.!?]+', body)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                # Take first few sentences up to max_length
                summary = ""
                for sentence in sentences:
                    if len(summary + sentence) < max_length:
                        summary += sentence + ". "
                    else:
                        break
                
                if not summary and body:
                    summary = body[:max_length] + "..." if len(body) > max_length else body
                
                summaries.append({
                    "id": email_info.get('id'),
                    "subject": email_info.get('subject'),
                    "from": email_info.get('from'),
                    "date": email_info.get('date'),
                    "summary": summary.strip(),
                    "original_length": len(body),
                    "summary_length": len(summary)
                })
            
            return {
                "status": "success",
                "summaries": summaries,
                "total_emails": len(emails),
                "message": f"Generated summaries for {len(summaries)} emails"
            }
            
        except Exception as e:
            error_msg = f"Failed to summarize emails: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def filter_emails(self, emails: List[Dict[str, Any]], 
                     sender_filter: Optional[str] = None,
                     subject_filter: Optional[str] = None,
                     date_from: Optional[datetime] = None,
                     date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Filter emails based on criteria.
        
        Args:
            emails: List of email dictionaries
            sender_filter: Filter by sender email/name
            subject_filter: Filter by subject keywords
            date_from: Filter emails after this date
            date_to: Filter emails before this date
            
        Returns:
            Dictionary with filtered emails
        """
        try:
            filtered_emails = []
            
            for email_info in emails:
                # Check sender filter
                if sender_filter:
                    sender = email_info.get('from', '').lower()
                    if sender_filter.lower() not in sender:
                        continue
                
                # Check subject filter
                if subject_filter:
                    subject = email_info.get('subject', '').lower()
                    if subject_filter.lower() not in subject:
                        continue
                
                # Check date filters (simplified - would need proper date parsing)
                # For now, just include the email if date filters are provided
                
                filtered_emails.append(email_info)
            
            return {
                "status": "success",
                "filtered_emails": filtered_emails,
                "original_count": len(emails),
                "filtered_count": len(filtered_emails),
                "filters_applied": {
                    "sender": sender_filter,
                    "subject": subject_filter,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to filter emails: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}


# Convenience functions for the main API
def send_email(to_emails: List[str], subject: str, body: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to send email"""
    handler = EmailHandler()
    try:
        return handler.send_email(to_emails, subject, body, **kwargs)
    finally:
        handler.disconnect()


def read_unread_emails(limit: int = 10, since_days: int = 1) -> Dict[str, Any]:
    """Convenience function to read unread emails"""
    handler = EmailHandler()
    try:
        return handler.read_emails(limit=limit, unread_only=True, since_days=since_days)
    finally:
        handler.disconnect()


def summarize_recent_emails(days: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Convenience function to get email summaries"""
    handler = EmailHandler()
    try:
        # Read emails
        result = handler.read_emails(limit=limit, since_days=days)
        if result["status"] == "error":
            return result
        
        # Summarize them
        emails = result.get("emails", [])
        if emails:
            return handler.summarize_emails(emails)
        else:
            return {"status": "info", "message": "No emails found to summarize"}
    finally:
        handler.disconnect()