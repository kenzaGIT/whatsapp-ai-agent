# test_email.py
import os
import asyncio
import sys
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env file
load_dotenv()

# Get the email credentials
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
EMAIL_SMTP_PORT = os.getenv("EMAIL_SMTP_PORT")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Check if all required variables are set
missing_vars = []
if not EMAIL_SMTP_SERVER:
    missing_vars.append("EMAIL_SMTP_SERVER")
if not EMAIL_SMTP_PORT:
    missing_vars.append("EMAIL_SMTP_PORT")
if not EMAIL_ADDRESS:
    missing_vars.append("EMAIL_ADDRESS")
if not EMAIL_PASSWORD:
    missing_vars.append("EMAIL_PASSWORD")

if missing_vars:
    print("Error: The following environment variables are missing:")
    for var in missing_vars:
        print(f"- {var}")
    print("\nPlease add them to your .env file.")
    sys.exit(1)

print("Email Service Test Script")
print("========================")
print(f"SMTP Server: {EMAIL_SMTP_SERVER}")
print(f"SMTP Port: {EMAIL_SMTP_PORT}")
print(f"Email Address: {EMAIL_ADDRESS}")
print(f"Password: {'*' * 8} (hidden)")

def test_email_connection():
    """Test connection to the email server"""
    try:
        print("\nTesting connection to email server...")
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, int(EMAIL_SMTP_PORT))
        server.starttls()
        
        print("Attempting to log in...")
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("✅ Login successful!")
        
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Error connecting to email server: {str(e)}")
        
        if "Authentication" in str(e):
            print("\nTroubleshooting authentication issues:")
            print("1. If using Gmail, make sure you're using an App Password, not your regular password")
            print("2. Check that your email address is correct")
            print("3. Verify that 2FA is enabled on your Google Account before generating an App Password")
        elif "Connection" in str(e):
            print("\nTroubleshooting connection issues:")
            print("1. Check that your SMTP server and port are correct")
            print("2. Verify that your network allows SMTP connections")
        
        return False

def send_test_email():
    """Send a test email to yourself"""
    try:
        print("\nAttempting to send a test email to yourself...")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS  # Sending to yourself for testing
        msg['Subject'] = "Test Email from WhatsApp AI Agent"
        
        body = """
        This is a test email sent from the WhatsApp AI Agent test script.
        
        If you're receiving this, your email configuration is working correctly!
        
        Best regards,
        Your WhatsApp AI Agent
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to server and send
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, int(EMAIL_SMTP_PORT))
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        server.send_message(msg)
        server.quit()
        
        print("✅ Test email sent successfully!")
        print(f"Check your inbox at {EMAIL_ADDRESS} for the test email.")
        return True
    except Exception as e:
        print(f"❌ Error sending test email: {str(e)}")
        return False

# Execute tests
if __name__ == "__main__":
    connection_ok = test_email_connection()
    
    if connection_ok:
        print("\nConnection test successful!")
        
        # Ask if the user wants to send a test email
        send_email = input("\nDo you want to send a test email to yourself? (y/n): ").lower()
        if send_email == 'y' or send_email == 'yes':
            send_test_email()
        else:
            print("Skipping test email.")
    else:
        print("\nConnection test failed. Please fix the issues before continuing.")