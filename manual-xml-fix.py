#!/usr/bin/env python3
"""
Manual fix for the XML issue in webhook handler
"""

def show_webhook_fix():
    """Show the exact lines to replace in main.py"""
    
    print("=== MANUAL FIX FOR XML ISSUE ===\n")
    print("In your main.py file, find the webhook_handler function and replace it with this:")
    print("\n" + "="*80)
    
    new_webhook_code = '''@app.post("/webhook", response_class=PlainTextResponse)
async def webhook_handler(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: int = Form(0),
):
    """Handle incoming WhatsApp messages via Twilio webhook"""
    print(f"Received message from {From}: {Body}")
    
    # Extract the user's phone number
    sender_id = From
    message_text = Body
    
    # Create a task to process the message asynchronously
    # This allows us to return a response to Twilio quickly
    asyncio.create_task(process_message(sender_id, message_text))
    
    # CRITICAL: This TwiML response is ONLY for Twilio's webhook
    # It should NEVER appear in the user's WhatsApp messages
    # User messages are sent separately in process_message()
    twiml_response = whatsapp.create_response_twiml()
    print(f"DEBUG: Returning TwiML to Twilio (not to user): {twiml_response}")
    
    return twiml_response'''
    
    print(new_webhook_code)
    print("="*80)
    
    print("\nALTERNATIVE APPROACH:")
    print("If the above doesn't work, try this simpler version:")
    print("\n" + "="*80)
    
    simple_webhook = '''@app.post("/webhook", response_class=PlainTextResponse)
async def webhook_handler(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: int = Form(0),
):
    """Handle incoming WhatsApp messages via Twilio webhook"""
    print(f"Received message from {From}: {Body}")
    
    # Process message asynchronously
    asyncio.create_task(process_message(From, Body))
    
    # Return empty TwiML response to Twilio
    return ""'''
    
    print(simple_webhook)
    print("="*80)

def check_whatsapp_connector():
    """Check if WhatsApp connector might be the issue"""
    print("\n=== CHECKING WHATSAPP CONNECTOR ===\n")
    
    print("Also check your connectors/whatsapp.py file.")
    print("Make sure the create_response_twiml method looks like this:")
    print("\n" + "="*60)
    
    correct_twiml = '''@staticmethod
def create_response_twiml(message: str = "") -> str:
    """
    Create a TwiML response for an incoming message
    
    Args:
        message: Optional message to send back (usually empty)
        
    Returns:
        TwiML response as string
    """
    response = MessagingResponse()
    # DO NOT add any message here unless you want it sent to the user
    # if message:
    #     response.message(message)
    return str(response)'''
    
    print(correct_twiml)
    print("="*60)

def show_debugging_steps():
    """Show debugging steps"""
    print("\n=== DEBUGGING STEPS ===\n")
    
    print("1. Make the changes above to main.py")
    print("2. Restart your agent: python start_agent.py")
    print("3. Send a test message and watch the terminal logs")
    print("4. Look for this line in the logs:")
    print("   'DEBUG: Returning TwiML to Twilio (not to user): ...'")
    print("5. If you still see XML in WhatsApp, the issue might be elsewhere")
    
    print("\n=== IF XML STILL APPEARS ===\n")
    print("The XML might be coming from:")
    print("- The send_message method in WhatsApp connector")
    print("- Some other part of the code calling create_response_twiml")
    print("- Twilio's webhook configuration")

def main():
    show_webhook_fix()
    check_whatsapp_connector()
    show_debugging_steps()
    
    print("\n=== SUMMARY ===")
    print("1. Fix webhook_handler in main.py (see above)")
    print("2. Optionally fix create_response_twiml in connectors/whatsapp.py")
    print("3. Restart and test")
    print("4. Run debug_calendar.py to test calendar fixes")

if __name__ == "__main__":
    main()