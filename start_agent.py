#start_agent.py
import os
import subprocess
import time
import signal
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBHOOK_PORT = int(os.getenv("PORT", "8000"))
NGROK_PORT = WEBHOOK_PORT
WEBHOOK_SCRIPT = "main.py"

# Process holders
webhook_process = None
ngrok_process = None

def start_webhook_server():
    """Start the webhook server"""
    print(f"Starting webhook server on port {WEBHOOK_PORT}...")
    return subprocess.Popen(
        ["python", WEBHOOK_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

def start_ngrok():
    """Start ngrok to create a tunnel"""
    print(f"Starting ngrok tunnel to port {NGROK_PORT}...")
    return subprocess.Popen(
        ["ngrok", "http", str(NGROK_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def get_ngrok_url():
    """Get the public URL from ngrok"""
    tries = 0
    max_tries = 10
    while tries < max_tries:
        try:
            response = subprocess.check_output(
                ["curl", "-s", "http://localhost:4040/api/tunnels"],
                universal_newlines=True
            )
            if "https://" in response:
                import json
                tunnels = json.loads(response)["tunnels"]
                for tunnel in tunnels:
                    if tunnel["proto"] == "https":
                        return tunnel["public_url"]
            tries += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error getting ngrok URL: {e}")
            tries += 1
            time.sleep(1)
    return None

def cleanup(signum=None, frame=None):
    """Clean up processes on exit"""
    print("\nShutting down...")
    
    if webhook_process:
        print("Terminating webhook server...")
        webhook_process.terminate()
        
    if ngrok_process:
        print("Terminating ngrok tunnel...")
        ngrok_process.terminate()
    
    print("Shutdown complete.")
    sys.exit(0)

def main():
    """Main function to start the WhatsApp AI Agent"""
    global webhook_process, ngrok_process
    
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Check for required environment variables
    required_vars = [
        ("GOOGLE_API_KEY", "for Gemini LLM"),
        ("GOOGLE_CREDENTIALS_PATH", "for Google Calendar"),
        ("GOOGLE_CALENDAR_ID", "for Google Calendar"),
        ("TWILIO_ACCOUNT_SID", "for WhatsApp"),
        ("TWILIO_AUTH_TOKEN", "for WhatsApp"),
        ("TWILIO_PHONE_NUMBER", "for WhatsApp")
    ]
    
    missing_vars = []
    for var_name, purpose in required_vars:
        if not os.getenv(var_name):
            missing_vars.append((var_name, purpose))
    
    if missing_vars:
        print("Missing required environment variables:")
        for var_name, purpose in missing_vars:
            print(f"- {var_name} ({purpose})")
        print("\nPlease add these to your .env file.")
        return
    
    # Start the webhook server
    webhook_process = start_webhook_server()
    print("Webhook server started!")
    
    # Give the webhook server time to start
    time.sleep(2)
    
    # Start ngrok
    ngrok_process = start_ngrok()
    print("Ngrok started!")
    
    # Give ngrok time to establish the tunnel
    time.sleep(2)
    
    # Get the ngrok URL
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print("Failed to get ngrok URL. Please check if ngrok is running properly.")
        cleanup()
        return
    
    webhook_url = f"{ngrok_url}/webhook"
    print("\n" + "=" * 80)
    print(f"WhatsApp AI Agent is running!")
    print(f"Public URL: {ngrok_url}")
    print("\nTo configure Twilio webhook:")
    print(f"1. Go to Twilio Console > WhatsApp > Sandbox")
    print(f"2. Set 'WHEN A MESSAGE COMES IN' to: {webhook_url}")
    print(f"3. Save your changes")
    print("=" * 80 + "\n")
    
    # Monitor the webhook process and print its output
    while True:
        try:
            # Check if the webhook process is still running
            if webhook_process.poll() is not None:
                print("Webhook server stopped unexpectedly.")
                cleanup()
                break
            
            # Read output from webhook process
            output = webhook_process.stdout.readline()
            if output:
                print(output.strip())
            
            error = webhook_process.stderr.readline()
            if error:
                print(f"ERROR: {error.strip()}")
            
            time.sleep(0.1)
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            cleanup()
            break

if __name__ == "__main__":
    main()
