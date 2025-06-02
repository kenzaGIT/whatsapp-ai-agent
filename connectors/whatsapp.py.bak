# connectors/whatsapp.py
import os
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

class TwilioWhatsAppConnector:
    """Connector for WhatsApp using Twilio"""
    
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, 
                 whatsapp_number: Optional[str] = None):
        """
        Initialize the Twilio WhatsApp connector
        
        Args:
            account_sid: Twilio account SID (default: from env vars)
            auth_token: Twilio auth token (default: from env vars)
            whatsapp_number: Your Twilio WhatsApp number with "whatsapp:" prefix (default: from env vars)
        """
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = whatsapp_number or os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        if not self.account_sid or not self.auth_token or not self.whatsapp_number:
            raise ValueError("Missing Twilio credentials. Please set TWILIO_ACCOUNT_SID, "
                             "TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_NUMBER in your .env file.")
        
        # Create Twilio client
        self.client = Client(self.account_sid, self.auth_token)
        
        print(f"Initialized Twilio WhatsApp connector with number: {self.whatsapp_number}")
    
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user
        
        Args:
            recipient_id: The recipient's phone number with country code (e.g., +1234567890)
            message: The message text to send
            
        Returns:
            Dict with status and message details
        """
        # Format the recipient ID for WhatsApp
        if not recipient_id.startswith("whatsapp:"):
            recipient_id = f"whatsapp:{recipient_id}"
        
        try:
            # Send the message through Twilio
            sent_message = self.client.messages.create(
                from_=self.whatsapp_number,
                body=message,
                to=recipient_id
            )
            
            return {
                "status": "success",
                "message_id": sent_message.sid,
                "details": {
                    "to": recipient_id,
                    "from": self.whatsapp_number,
                    "status": sent_message.status
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to send WhatsApp message: {str(e)}"
            }
    
    async def send_message_with_media(self, recipient_id: str, message: str, 
                                     media_url: str) -> Dict[str, Any]:
        """
        Send a message with media attachment to a WhatsApp user
        
        Args:
            recipient_id: The recipient's phone number with country code
            message: The message text to send
            media_url: URL to the media file (image, PDF, etc.)
            
        Returns:
            Dict with status and message details
        """
        # Format the recipient ID for WhatsApp
        if not recipient_id.startswith("whatsapp:"):
            recipient_id = f"whatsapp:{recipient_id}"
        
        try:
            # Send the message with media through Twilio
            sent_message = self.client.messages.create(
                from_=self.whatsapp_number,
                body=message,
                media_url=[media_url],
                to=recipient_id
            )
            
            return {
                "status": "success",
                "message_id": sent_message.sid,
                "details": {
                    "to": recipient_id,
                    "from": self.whatsapp_number,
                    "status": sent_message.status,
                    "media_url": media_url
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to send WhatsApp message with media: {str(e)}"
            }
    
    @staticmethod
    def parse_incoming_message(request_form: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse an incoming WhatsApp message from Twilio webhook
        
        Args:
            request_form: The form data from the webhook request
            
        Returns:
            Dict with parsed message data
        """
        try:
            # Extract the important information from the request
            message_data = {
                "message_sid": request_form.get("MessageSid", ""),
                "from": request_form.get("From", ""),  # Format: whatsapp:+1234567890
                "to": request_form.get("To", ""),      # Format: whatsapp:+1234567890
                "body": request_form.get("Body", ""),
                "num_media": int(request_form.get("NumMedia", "0")),
                "media_urls": []
            }
            
            # Extract any media URLs if present
            for i in range(message_data["num_media"]):
                media_url = request_form.get(f"MediaUrl{i}")
                if media_url:
                    message_data["media_urls"].append(media_url)
            
            # Extract the plain phone number (remove "whatsapp:" prefix)
            if message_data["from"].startswith("whatsapp:"):
                message_data["from_phone"] = message_data["from"][9:]
            else:
                message_data["from_phone"] = message_data["from"]
                
            return {
                "status": "success",
                "message": message_data
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to parse incoming WhatsApp message: {str(e)}"
            }
    
    @staticmethod
    def create_response_twiml(message: str = "") -> str:
        """
        Create a TwiML response for an incoming message
        
        Args:
            message: Optional message to send back
            
        Returns:
            TwiML response as string
        """
        response = MessagingResponse()
        if message:
            response.message(message)
        return str(response)


# Example usage
if __name__ == "__main__":
    # For testing purposes
    import asyncio
    
    async def test_whatsapp():
        # Create connector
        connector = TwilioWhatsAppConnector()
        
        # Ask for a recipient number
        recipient = input("Enter recipient WhatsApp number (with country code, e.g., +1234567890): ")
        
        # Send a test message
        result = await connector.send_message(recipient, "Hello from the WhatsApp AI Agent! This is a test message.")
        print(f"Message sent: {result}")
    
    # Run the test
    asyncio.run(test_whatsapp())