#!/usr/bin/env python3
"""
Check the WhatsApp AI Agent project structure to ensure all required files exist.
"""

import os
import sys

def check_project_files():
    """Check if all required project files exist"""
    
    # Define the expected project structure
    required_files = [
        # Root files
        ".env",
        "full_webhook_handler.py",
        "start_agent.py",
        "requirements.txt",
        
        # Agent module
        "agent/__init__.py",
        "agent/llm.py",
        "agent/reasoning.py",
        "agent/action_planner.py",
        
        # Connectors module
        "connectors/__init__.py",
        "connectors/whatsapp.py",
        "connectors/calendar_api.py",
        "connectors/email_api.py",
        
        # Utils module
        "utils/__init__.py",
        "utils/message_parser.py",
        "utils/response_formatter.py"
    ]
    
    # Check each file
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    # Print results
    print("\n=== Project Structure Check ===")
    if missing_files:
        print(f"❌ Missing {len(missing_files)} required files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease create these files before running start_agent.py")
    else:
        print("✅ All required files are present.")
    
    # Check credentials directory
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
    if credentials_path:
        credentials_dir = os.path.dirname(credentials_path)
        if not os.path.exists(credentials_dir):
            print(f"\n❌ Credentials directory not found: {credentials_dir}")
            print(f"   Create this directory and place your Google Calendar credentials file inside it.")
    
    return len(missing_files) == 0

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: dotenv package not installed. Install with: pip install python-dotenv")
    
    # Check project structure
    if check_project_files():
        print("\nProject structure looks good! You can now run test_dependencies.py for more checks.")
    else:
        print("\nFix the missing files before continuing.")
        sys.exit(1)