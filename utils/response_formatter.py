# utils/response_formatter.py
from typing import Dict, Any, List

class ResponseFormatter:
    """Format responses for WhatsApp"""
    
    @staticmethod
    def format_calendar_events(events: List[Dict[str, Any]]) -> str:
        """
        Format a list of calendar events for WhatsApp
        
        Args:
            events: List of calendar event data
            
        Returns:
            Formatted message text
        """
        if not events:
            return "No events found."
        
        lines = ["*Your schedule:*"]
        
        for i, event in enumerate(events, 1):
            start = event.get("start", "").replace("T", " ").replace("Z", "")
            if len(start) > 16:  # Trim seconds
                start = start[:16]
                
            summary = event.get("summary", "Untitled event")
            location = event.get("location", "")
            location_text = f" at {location}" if location else ""
            
            lines.append(f"{i}. {start} - *{summary}*{location_text}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_emails(emails: List[Dict[str, Any]]) -> str:
        """
        Format a list of emails for WhatsApp
        
        Args:
            emails: List of email data
            
        Returns:
            Formatted message text
        """
        if not emails:
            return "No emails found."
        
        lines = ["*Recent emails:*"]
        
        for i, email in enumerate(emails, 1):
            subject = email.get("subject", "No subject")
            sender = email.get("from", "Unknown sender").split("<")[0].strip()
            preview = email.get("body_preview", "")
            
            lines.append(f"{i}. From: *{sender}*\n   Subject: {subject}\n   {preview}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_error(error_message: str) -> str:
        """
        Format an error message for WhatsApp
        
        Args:
            error_message: The error message
            
        Returns:
            Formatted error message
        """
        return f"❌ *Error:* {error_message}\n\nPlease try again or rephrase your request."
    
    @staticmethod
    def format_calendar_event_created(event_data: Dict[str, Any]) -> str:
        """
        Format a message for a newly created calendar event
        
        Args:
            event_data: Calendar event data
            
        Returns:
            Formatted message text
        """
        summary = event_data.get("summary", "Untitled event")
        start = event_data.get("start", "").replace("T", " ").replace("Z", "")
        if len(start) > 16:  # Trim seconds
            start = start[:16]
            
        location = event_data.get("location", "")
        location_text = f" at *{location}*" if location else ""
        
        return f"✅ Event created successfully!\n\n*{summary}*\nScheduled for: {start}{location_text}"
    
    @staticmethod
    def format_calendar_event_updated(event_data: Dict[str, Any]) -> str:
        """
        Format a message for an updated calendar event
        
        Args:
            event_data: Updated calendar event data
            
        Returns:
            Formatted message text
        """
        summary = event_data.get("summary", "Untitled event")
        start = event_data.get("start", "").replace("T", " ").replace("Z", "")
        if len(start) > 16:  # Trim seconds
            start = start[:16]
            
        location = event_data.get("location", "")
        location_text = f" at *{location}*" if location else ""
        
        return f"✅ Event updated successfully!\n\n*{summary}*\nNew time: {start}{location_text}"
    
    @staticmethod
    def format_calendar_event_deleted(event_id: str) -> str:
        """
        Format a message for a deleted calendar event
        
        Args:
            event_id: ID of the deleted event
            
        Returns:
            Formatted message text
        """
        return f"✅ Event deleted successfully!"
    
    @staticmethod
    def format_email_sent(to: str, subject: str) -> str:
        """
        Format a message for a sent email
        
        Args:
            to: Recipient email address
            subject: Email subject
            
        Returns:
            Formatted message text
        """
        return f"✅ Email sent successfully!\n\nTo: *{to}*\nSubject: *{subject}*"
    
    @staticmethod
    def format_verification_request(action_summary: str) -> str:
        """
        Format a verification request message
        
        Args:
            action_summary: Summary of the planned action
            
        Returns:
            Formatted verification request
        """
        return (
            f"I'll help you with this. Here's what I'm planning to do:\n\n"
            f"{action_summary}\n\n"
            f"Would you like me to proceed? (yes/no)"
        )
    
    @staticmethod
    def format_thinking_message() -> str:
        """
        Format a 'thinking' message
        
        Returns:
            Formatted thinking message
        """
        return "🤔 Thinking about your request..."
    
    @staticmethod
    def format_processing_message() -> str:
        """
        Format a 'processing' message
        
        Returns:
            Formatted processing message
        """
        return "⚙️ Processing your request..."
    
    @staticmethod
    def format_welcome_message() -> str:
        """
        Format a welcome message
        
        Returns:
            Formatted welcome message
        """
        return (
            "*Welcome to your AI Assistant!* 👋\n\n"
            "I can help you with:\n"
            "• Managing your calendar\n"
            "• Sending and reading emails\n"
            "• Finding information\n\n"
            "Just tell me what you need in natural language!"
        )