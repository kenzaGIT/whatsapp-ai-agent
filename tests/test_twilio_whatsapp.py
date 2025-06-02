# test_twilio_whatsapp.py
import os
import asyncio
from dotenv import load_dotenv
import sys

# Add project directory to path
sys.path.append(".")

# Import the WhatsApp connector
from connectors.whatsapp import TwilioWhatsAppConnector

# Load environment variables
load_dotenv()

async def test_twilio_whatsapp():
    """Test the Twilio WhatsApp integration"""
    print("Twilio WhatsApp Integration Test")
    print("================================")
    
    # Check for required environment variables
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    missing_vars = []
    if not account_sid:
        missing_vars.append("TWILIO_ACCOUNT_SID")
    if not auth_token:
        missing_vars.append("TWILIO_AUTH_TOKEN")
    if not whatsapp_number:
        missing_vars.append("TWILIO_WHATSAPP_NUMBER")
    
    if missing_vars:
        print("Error: The following environment variables are missing:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease add them to your .env file.")
        return
    
    print("Found Twilio credentials:")
    print(f"- Account SID: {account_sid[:5]}...{account_sid[-5:]}")
    print(f"- Auth Token: {auth_token[:5]}...{auth_token[-5:]}")
    print(f"- WhatsApp Number: {whatsapp_number}")
    
    # Create the WhatsApp connector
    try:
        print("\nInitializing WhatsApp connector...")
        whatsapp = TwilioWhatsAppConnector()
        print("✅ WhatsApp connector initialized successfully!")
        
        # Send a test message
        recipient = input("\nEnter your WhatsApp number to receive a test message (with country code, e.g., +1234567890): ")
        
        print(f"\nSending test message to {recipient}...")
        result = await whatsapp.send_message(
            recipient_id=recipient,
            message="Hello! This is a test message from your WhatsApp AI Agent. If you're seeing this, the Twilio WhatsApp integration is working correctly!"
        )
        
        if result.get("status") == "success":
            print("✅ Test message sent successfully!")
            print(f"Message ID: {result.get('message_id')}")
            print("Check your WhatsApp for the test message.")
            
            # Instructions for further testing
            print("\n=== Next Steps ===")
            print("1. Once you receive the message, reply to it to test the webhook setup")
            print("2. Set up ngrok to expose your local server to the internet:")
            print("   - Download ngrok from https://ngrok.com/download")
            print("   - Run: ngrok http 8000")
            print("3. Configure the Twilio webhook URL with your ngrok URL:")
            print("   - Go to the Twilio Console > WhatsApp > Sandbox")
            print("   - Set the 'WHEN A MESSAGE COMES IN' field to https://your-ngrok-url/webhook")
            print("4. Run your webhook_handler.py to start the server:")
            print("   - python webhook_handler.py")
            
        else:
            print(f"❌ Failed to send test message: {result.get('message')}")
            print("Troubleshooting:")
            print("1. Verify your Twilio credentials are correct")
            print("2. Make sure your WhatsApp number has joined the Twilio sandbox")
            print("3. Check if your Twilio account has available credit")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_twilio_whatsapp())