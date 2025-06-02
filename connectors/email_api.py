# connectors/email_api.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
from email.header import decode_header
from typing import Dict, Any, List, Optional
import asyncio
import re
import html

class EmailService:
    """Service for sending and receiving emails"""
    
    def __init__(self, smtp_server: str, smtp_port: int, email: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
        self.imap_server = f"imap.{smtp_server.split('.', 1)[1]}"  # Convert smtp.gmail.com to imap.gmail.com
    
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a method on the email service
        
        Args:
            method: The method to execute (e.g., 'send_email', 'list_emails')
            params: Parameters for the method
            
        Returns:
            The result of the operation
        """
        method_map = {
            'send_email': self.send_email,
            'list_emails': self.list_emails,
            'search_emails': self.search_emails
        }
        
        if method not in method_map:
            return {"error": f"Unknown method: {method}"}
        
        return await method_map[method](**params)
    
    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            
        Returns:
            Status of the operation
        """
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(self._send_email_sync, to, subject, body)
    
    def _send_email_sync(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Synchronous implementation of send_email"""
        msg = MIMEMultipart()
        msg['From'] = self.email
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            text = msg.as_string()
            server.sendmail(self.email, to, text)
            server.quit()
            
            return {
                "status": "success",
                "message": f"Email sent to {to}",
                "details": {
                    "to": to,
                    "subject": subject
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}"
            }
    
    async def list_emails(self, folder: str = "INBOX", limit: int = 5) -> Dict[str, Any]:
        """
        List recent emails from a folder
        
        Args:
            folder: Email folder (default: INBOX)
            limit: Maximum number of emails to retrieve
            
        Returns:
            List of emails
        """
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(self._list_emails_sync, folder, limit)
    
    def _list_emails_sync(self, folder: str = "INBOX", limit: int = 5) -> Dict[str, Any]:
        """Synchronous implementation of list_emails"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.select(folder)
            
            _, data = mail.search(None, "ALL")
            email_ids = data[0].split()
            
            # Get the last 'limit' emails
            start_index = max(0, len(email_ids) - limit)
            email_ids = email_ids[start_index:]
            
            emails = []
            for email_id in reversed(email_ids):  # Process newest first
                _, msg_data = mail.fetch(email_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Get subject
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # Get sender
                from_header = decode_header(msg["From"])[0][0]
                if isinstance(from_header, bytes):
                    from_header = from_header.decode()
                
                # Get date
                date = msg["Date"]
                
                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = "Could not decode message body"
                
                # Clean and truncate body
                body = re.sub(r'\s+', ' ', body).strip()
                body = html.unescape(body)
                if len(body) > 200:
                    body = body[:200] + "..."
                
                emails.append({
                    "id": email_id.decode(),
                    "subject": subject,
                    "from": from_header,
                    "date": date,
                    "body_preview": body
                })
            
            mail.close()
            mail.logout()
            
            return {
                "status": "success",
                "count": len(emails),
                "emails": emails
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list emails: {str(e)}"
            }
    
    async def search_emails(self, query: str, folder: str = "INBOX", limit: int = 5) -> Dict[str, Any]:
        """
        Search for emails matching a query
        
        Args:
            query: Search query
            folder: Email folder to search
            limit: Maximum number of results
            
        Returns:
            Matching emails
        """
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(self._search_emails_sync, query, folder, limit)
    
    def _search_emails_sync(self, query: str, folder: str = "INBOX", limit: int = 5) -> Dict[str, Any]:
        """Synchronous implementation of search_emails"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.select(folder)
            
            # Convert the query to IMAP search criteria
            search_criteria = f'(OR SUBJECT "{query}" OR FROM "{query}" OR BODY "{query}")'
            _, data = mail.search(None, search_criteria)
            email_ids = data[0].split()
            
            # Limit the number of results
            if len(email_ids) > limit:
                email_ids = email_ids[-limit:]
            
            emails = []
            for email_id in reversed(email_ids):  # Process newest first
                _, msg_data = mail.fetch(email_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Get subject
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # Get sender
                from_header = decode_header(msg["From"])[0][0]
                if isinstance(from_header, bytes):
                    from_header = from_header.decode()
                
                # Get date
                date = msg["Date"]
                
                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = "Could not decode message body"
                
                # Clean and truncate body
                body = re.sub(r'\s+', ' ', body).strip()
                body = html.unescape(body)
                if len(body) > 200:
                    body = body[:200] + "..."
                
                emails.append({
                    "id": email_id.decode(),
                    "subject": subject,
                    "from": from_header,
                    "date": date,
                    "body_preview": body,
                    "matched_query": query
                })
            
            mail.close()
            mail.logout()
            
            return {
                "status": "success",
                "count": len(emails),
                "query": query,
                "emails": emails
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to search emails: {str(e)}"
            }
            
    async def reply_to_email(self, email_id: str, body: str, folder: str = "INBOX") -> Dict[str, Any]:
        """
        Reply to an existing email
        
        Args:
            email_id: ID of the email to reply to
            body: Reply body
            folder: Folder containing the email
            
        Returns:
            Status of the operation
        """
        # Get the original email details
        mail = imaplib.IMAP4_SSL(self.imap_server)
        
        try:
            mail.login(self.email, self.password)
            mail.select(folder)
            
            _, msg_data = mail.fetch(email_id.encode(), "(RFC822)")
            raw_email = msg_data[0][1]
            original_msg = email.message_from_bytes(raw_email)
            
            # Get original sender (will be the recipient of our reply)
            from_header = decode_header(original_msg["From"])[0][0]
            if isinstance(from_header, bytes):
                from_header = from_header.decode()
                
            # Extract email address from "Name <email@example.com>" format
            to_email = re.search(r'<(.+?)>', from_header)
            if to_email:
                to_email = to_email.group(1)
            else:
                to_email = from_header
                
            # Get subject and add Re: if not already present
            subject = decode_header(original_msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
                
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
                
            # Close the connection
            mail.close()
            mail.logout()
            
            # Send the reply
            return await self.send_email(to=to_email, subject=subject, body=body)
            
        except Exception as e:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass
                    
            return {
                "status": "error",
                "message": f"Failed to reply to email: {str(e)}"
            }