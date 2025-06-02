#!/usr/bin/env python3
"""
Test TwiML response formatting
"""
import os
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from connectors.whatsapp import TwilioWhatsAppConnector

# Load environment variables
load_dotenv()

def test_twiml_response():
    """Test TwiML response formatting"""
    print("\n=== Testing TwiML Response Formatting ===\n")
    
    # Create a basic TwiML response
    response = MessagingResponse()
    twiml_str = str(response)
    
    print(f"Basic TwiML response: {twiml_str}")
    
    # Create a TwiML response with a message
    response_with_msg = MessagingResponse()
    response_with_msg.message("This is a test message")
    twiml_with_msg_str = str(response_with_msg)
    
    print(f"TwiML with message: {twiml_with_msg_str}")
    
    # Test the connector's create_response_twiml method
    whatsapp = TwilioWhatsAppConnector()
    connector_twiml = whatsapp.create_response_twiml()
    
    print(f"Connector TwiML response: {connector_twiml}")
    
    # Verify the connector's response is a string
    is_string = isinstance(connector_twiml, str)
    print(f"Connector response is a string: {is_string}")
    
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    test_twiml_response()
