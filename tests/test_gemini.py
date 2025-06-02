# test_gemini_fixed2.py
import os
import asyncio
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Get the Google API key from environment variables
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment variables.")
    print("Make sure you have created a .env file with your Google API key.")
    sys.exit(1)

print(f"Found Google API key: {api_key[:5]}...{api_key[-4:] if len(api_key) > 8 else ''}")

# List of recommended models to try in order of preference
RECOMMENDED_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-pro",
]

async def test_gemini_connection():
    """Test the connection to Google Gemini API"""
    try:
        print("Testing connection to Google Gemini API...")
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # List available models
        print("\nListing available models:")
        models = genai.list_models()
        
        # Filter for non-vision, non-deprecated models
        suitable_models = []
        for model in models:
            model_name = model.name.lower()
            # Skip vision models and embeddings
            if "vision" in model_name or "embedding" in model_name:
                continue
            # Take only the model name without path
            short_name = model.name.split('/')[-1]
            suitable_models.append((model.name, short_name))
        
        print("Available suitable models:")
        for full_name, short_name in suitable_models:
            print(f" - {full_name}")
        
        # Try to find one of our recommended models
        selected_model = None
        
        # First try our recommended models in order
        for recommended in RECOMMENDED_MODELS:
            for full_name, short_name in suitable_models:
                if recommended in short_name:
                    selected_model = full_name
                    break
            if selected_model:
                break
                
        # If no recommended model is found, use the first suitable model
        if not selected_model and suitable_models:
            selected_model = suitable_models[0][0]
            
        if not selected_model:
            print("\n❌ No suitable models found!")
            return False
            
        print(f"\nUsing model: {selected_model}")
        
        # Set up the model
        model = genai.GenerativeModel(selected_model)
        
        # Make a simple API call
        print("\nSending test message...")
        response = model.generate_content("Hello, are you working? Please respond with a short message.")
        
        # Get the response text
        message = response.text
        
        print("\n✅ Success! Received response from Google Gemini:")
        print(f"Response: \"{message}\"")
        print("\nYour Google Gemini API key is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error connecting to Google Gemini: {str(e)}")
        
        # Provide troubleshooting guidance based on error type
        if "API key" in str(e) or "key is invalid" in str(e):
            print("\nTroubleshooting API key issues:")
            print("1. Check that your Google AI Studio API key is correct")
            print("2. Make sure your Google Cloud project has the Gemini API enabled")
            print("3. Verify your API key hasn't been revoked")
        elif "quota" in str(e).lower():
            print("\nTroubleshooting quota issues:")
            print("1. You may have exceeded your quota limits")
            print("2. Check your Google AI Studio dashboard for quota information")
        elif "model" in str(e).lower() or "deprecated" in str(e).lower():
            print("\nTroubleshooting model issues:")
            print("1. The model tried has been deprecated or isn't available in your region")
            print("2. Try getting a new API key from Google AI Studio")
            print("3. Update the list of RECOMMENDED_MODELS in the script")
        
        return False

# Run the test
if __name__ == "__main__":
    print("Google Gemini API Test Script (Fixed v2)")
    print("=======================================")
    asyncio.run(test_gemini_connection())