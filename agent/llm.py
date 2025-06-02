#llm.py
import google.generativeai as genai
from typing import Dict, Any, Optional, List
import json
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMService:
    """Service to interact with Google Gemini models"""
    
    # Updated recommended models to try in order of preference - matching your test_gemini_fixed2.py
    RECOMMENDED_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-pro",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini LLM service
        
        Args:
            api_key: Google AI Studio API key (default: from env vars)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("No Google API key provided. Set GOOGLE_API_KEY in your .env file.")
        
        # Configure the Google Generative AI library
        genai.configure(api_key=self.api_key)
        
        # Find the best available model
        self.model = self._find_best_model()
        
        # Set up the model with default generation config
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        # Create the generative model
        self.gemini_model = genai.GenerativeModel(
            model_name=self.model,
            generation_config=generation_config
        )
        
        print(f"Initialized Google Gemini LLM with model: {self.model}")
    
    def _find_best_model(self) -> str:
        """Find the best available Gemini model"""
        try:
            # List available models
            models = genai.list_models()
            
            # Filter for suitable models (non-vision, non-embedding)
            suitable_models = []
            for model in models:
                model_name = model.name.lower()
                # Skip vision models and embeddings
                if "vision" in model_name or "embedding" in model_name:
                    continue
                # Store both full name and short name
                short_name = model.name.split('/')[-1]
                suitable_models.append((model.name, short_name))
            
            print(f"Available suitable models: {[m[0] for m in suitable_models]}")
            
            # Try to find one of our recommended models
            for recommended in self.RECOMMENDED_MODELS:
                for full_name, short_name in suitable_models:
                    if recommended in short_name:
                        return full_name
            
            # If no recommended model is found, use the first suitable model
            if suitable_models:
                return suitable_models[0][0]
            
            # If no models found, raise an error
            raise ValueError("No suitable Gemini models available for this API key")
            
        except Exception as e:
            print(f"Error finding best model: {str(e)}")
            # Use a more generic fallback that might be available in most regions
            return "models/gemini-1.5-flash"
    
    async def generate(self, 
                      prompt: str, 
                      system_message: Optional[str] = None, 
                      temperature: float = 0.7, 
                      max_tokens: int = 1000) -> str:
        """
        Generate text using Gemini
        
        Args:
            prompt: The user's input prompt
            system_message: Optional system message/instruction
            temperature: Creativity of the response (0.0-1.0)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Generated text response
        """
        # Combine system message and prompt if needed
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Adjust generation config with the provided parameters
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
            "top_k": 40
        }
        
        try:
            # Run in a thread pool to make it async-compatible
            return await asyncio.to_thread(self._generate_sync, full_prompt, generation_config)
        except Exception as e:
            print(f"Error generating response from Gemini: {str(e)}")
            # Return a fallback message instead of raising exception
            return f"Sorry, I encountered an error while generating a response: {str(e)}"
    
    def _generate_sync(self, prompt: str, generation_config: Dict[str, Any]) -> str:
        """Synchronous implementation of text generation"""
        # Update the generation config
        self.gemini_model.generation_config = generation_config
        
        try:
            # Generate content
            response = self.gemini_model.generate_content(prompt)
            
            # Return the response text
            return response.text
        except Exception as e:
            print(f"Error in generate_content: {str(e)}")
            return f"Error generating content: {str(e)}"
    
    async def structured_generate(self, 
                                 prompt: str, 
                                 output_schema: Dict[str, Any],
                                 system_message: Optional[str] = None,
                                 temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate structured JSON output
        
        Args:
            prompt: The user's input prompt
            output_schema: JSON schema for the expected output
            system_message: Optional system message/instruction
            temperature: Creativity of the response (0.0-1.0)
            
        Returns:
            Structured data based on the provided schema
        """
        # Create a prompt that requests structured JSON output
        schema_str = json.dumps(output_schema, indent=2)
        structured_prompt = f"""
        {prompt}
        
        Please provide your response as a valid JSON object that conforms to the following schema:
        {schema_str}
        
        Your response must be valid, parseable JSON that matches this schema exactly.
        Don't include any explanations, notes, or text outside of the JSON structure.
        Return ONLY the JSON object and nothing else.
        """
        
        if system_message:
            structured_prompt = f"{system_message}\n\n{structured_prompt}"
        
        # Maximum attempts for getting valid JSON
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            try:
                # Get the text response
                json_text = await self.generate(
                    prompt=structured_prompt,
                    temperature=temperature
                )
                
                # Extract JSON from the response (handle cases where model might add notes)
                json_text = self._extract_json(json_text)
                
                # Parse the JSON
                result = json.loads(json_text)
                return result
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response (attempt {attempt}/{max_attempts}): {str(e)}")
                if attempt >= max_attempts:
                    print(f"Raw response: {json_text}")
                    # Return a default fallback response instead of raising an exception
                    return {"error": "Failed to generate valid JSON response", "fallback": True}
                # Lower temperature for next attempt to get cleaner output
                temperature = max(0.1, temperature - 0.2)
            except Exception as e:
                print(f"Error generating structured response: {str(e)}")
                # Return a default fallback response
                return {"error": f"Error: {str(e)}", "fallback": True}
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might contain other content"""
        import re
        
        # First, try to find text between ``` markers (code blocks)
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            potential_json = code_block_match.group(1).strip()
            if potential_json.startswith('{') and potential_json.endswith('}'):
                return potential_json
        
        # Then try to find everything between first { and last }
        json_match = re.search(r'({[\s\S]*})', text)
        if json_match:
            return json_match.group(1)
            
        # If all else fails, return the original text
        return text