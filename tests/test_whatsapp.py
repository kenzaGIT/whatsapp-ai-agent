# test_whatsapp.py
import os
import asyncio
import sys
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables from .env file
load_dotenv()

# Get the WhatsApp API credentials
WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID")
WA_ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN")

# Check if all required variables are set
missing_vars = []
if not WA_PHONE_NUMBER_ID:
    missing_vars.append("WA_PHONE_NUMBER_ID")
if not WA_ACCESS_TOKEN:
    missing_vars.append("WA_ACCESS_TOKEN")

if missing_vars:
    print("Error: The following environment variables are missing:")
    for var in missing_vars:
        print(f"- {var}")
    print("\nPlease add them to your .env file.")
    sys.exit(1)

print("WhatsApp Business API Test Script")
print("================================")
print(f"Phone Number ID: {WA_PHONE_NUMBER_ID}")
print(f"Access Token: {'*' * 8}...{'*' * 8} (hidden)")

async def test_whatsapp_connection():
    """Test connection to WhatsApp Business API by getting account info"""
    api_url = f"https://graph.facebook.com/v17.0/{WA_PHONE_NUMBER_ID}"
    
    headers = {
        "Authorization": f"Bearer {WA_ACCESS_TOKEN}"
    }
    
    try:
        print("\nTesting connection to WhatsApp Business API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Successfully connected to WhatsApp Business API!")
                    print("Account information:")
                    print(f" - Account ID: {data.get('id', 'N/A')}")
                    print(f" - Phone Number: {data.get('display_phone_number', 'N/A')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Error connecting to WhatsApp API: {response.status}")
                    print(f"Error details: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Error connecting to WhatsApp API: {str(e)}")
        return False

async def send_test_message():
    """Send a test message to a specified recipient"""
    recipient = input("\nEnter a WhatsApp number to send a test message to (include country code, e.g., +1234567890): ")
    
    # Remove any spaces or special characters
    recipient = recipient.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Add + if not present
    if not recipient.startswith("+"):
        recipient = "+" + recipient
    
    # Confirm the number
    confirm = input(f"Confirm sending a test message to {recipient}? (y/n): ").lower()
    if confirm != 'y' and confirm != 'yes':
        print("Test message canceled.")
        return False
    
    api_url = f"https://graph.facebook.com/v17.0/{WA_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WA_ACCESS_TOKEN}"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {
            "body": "This is a test message from the WhatsApp AI Agent. If you're receiving this, the WhatsApp API is working correctly!"
        }
    }
    
    try:
        print(f"\nSending test message to {recipient}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    print("✅ Test message sent successfully!")
                    print(f"Message ID: {response_data.get('messages', [{}])[0].get('id', 'N/A')}")
                    return True
                else:
                    print(f"❌ Error sending test message: {response.status}")
                    print(f"Error details: {response_data}")
                    
                    if "error" in response_data:
                        error = response_data["error"]
                        print(f"Error type: {error.get('type', 'N/A')}")
                        print(f"Error message: {error.get('message', 'N/A')}")
                        
                        if "message" in error and "permission" in error["message"].lower():
                            print("\nTroubleshooting permission issues:")
                            print("1. Make sure your WhatsApp Business account is properly set up")
                            print("2. Verify that your access token has the correct permissions")
                            print("3. Check if you need to add the recipient as a test user")
                    
                    return False
    except Exception as e:
        print(f"❌ Error sending test message: {str(e)}")
        return False

# Execute tests
if __name__ == "__main__":
    print("Note: For the WhatsApp Business API to work, you need:")
    print("1. A Meta Developers account")
    print("2. A WhatsApp Business account")
    print("3. Proper API credentials")
    print("4. For test accounts, numbers need to be registered as test users\n")
    
    # Run the tests
    asyncio.run(test_whatsapp_connection())
    
    # If connection test passed, offer to send test message
    send_message = input("\nDo you want to send a test message? (y/n): ").lower()
    if send_message == 'y' or send_message == 'yes':
        asyncio.run(send_test_message())
    else:
        print("Skipping test message.")