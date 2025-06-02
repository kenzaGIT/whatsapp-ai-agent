# agent/reasoning.py
from typing import Dict, Any, List, Optional
from agent.llm import LLMService
import json

class ChainOfThoughtReasoner:
    """Implements chain-of-thought reasoning using an LLM"""
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        
    async def reason(self,
                  prompt: str,
                  intent: Dict[str, Any],
                  context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generate reasoning steps for the given message
        
        Args:
            prompt: The user's input message
            intent: Parsed intent from the message
            context: Additional context information
            
        Returns:
            List of reasoning steps
        """
        # Special handling for free time queries
        if "when am i free" in prompt.lower() or "find free time" in prompt.lower() or "free slots" in prompt.lower():
            # Add reasoning steps for free time query
            reasoning_steps = [
                {
                    "step_number": 1,
                    "description": "Understand the user's request for free time information",
                    "reasoning": "The user wants to know when they are free in their calendar, which requires checking their schedule for available time slots.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 2,
                    "description": "Determine the time frame for checking free slots",
                    "reasoning": "I need to identify the date or time range the user is asking about to properly search for free time.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 3,
                    "description": "Query the calendar for free time slots",
                    "reasoning": "I will use the calendar service to find available time slots in the user's calendar for the specified time frame.",
                    "required_services": ["calendar"]
                }
            ]
            return reasoning_steps
        
        # Special handling for event search queries
        if "find my meeting" in prompt.lower() or "search for events" in prompt.lower() or "find events" in prompt.lower():
            # Add reasoning steps for event search
            reasoning_steps = [
                {
                    "step_number": 1,
                    "description": "Understand the user's request to find specific events",
                    "reasoning": "The user wants to find specific events or meetings in their calendar based on certain criteria.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 2,
                    "description": "Extract search criteria from the request",
                    "reasoning": "I need to determine what criteria to use for searching (e.g., person name, topic, date range).",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 3,
                    "description": "Search the calendar for matching events",
                    "reasoning": "I will use the calendar service to find events that match the specified criteria.",
                    "required_services": ["calendar"]
                }
            ]
            return reasoning_steps
        
        # Special handling for event rescheduling
        if "reschedule" in prompt.lower() or "move my meeting" in prompt.lower() or "change the time" in prompt.lower():
            # Add reasoning steps for rescheduling
            reasoning_steps = [
                {
                    "step_number": 1,
                    "description": "Understand the user's request to reschedule an event",
                    "reasoning": "The user wants to change the time of an existing calendar event.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 2,
                    "description": "Identify the event to reschedule",
                    "reasoning": "I need to determine which specific event the user wants to reschedule based on the details provided.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 3,
                    "description": "Determine the new time for the event",
                    "reasoning": "I need to extract the new desired time for the event from the user's request.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 4,
                    "description": "Check for conflicts at the new time",
                    "reasoning": "I should verify if there are any scheduling conflicts at the proposed new time.",
                    "required_services": ["calendar"]
                },
                {
                    "step_number": 5,
                    "description": "Update the calendar event",
                    "reasoning": "I will use the calendar service to reschedule the event to the new time.",
                    "required_services": ["calendar"]
                }
            ]
            return reasoning_steps
        
        # Default handling for other queries
        system_message = """
        You are an AI assistant that thinks step-by-step before taking action.
        For each user request, break down your reasoning process into clear steps.
        Consider what information you need, what services to use, and what specific actions to take.
        """
        
        reasoning_prompt = f"""
        User request: "{prompt}"
        
        Detected intent: {json.dumps(intent, indent=2)}
        
        Additional context: {json.dumps(context, indent=2) if context else '{}'}
        
        Think step-by-step about how to fulfill this request. Break down your reasoning:
        1. What is the user asking for specifically?
        2. What information or actions are needed to fulfill this request?
        3. Which services would you need to use (email, calendar)?
        4. What are the specific steps required to complete this task?
        """
        
        output_schema = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "List of reasoning steps",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer"},
                            "description": {"type": "string"},
                            "reasoning": {"type": "string"},
                            "required_services": {
                                "type": "array", 
                                "items": {"type": "string", "enum": ["email", "calendar"]}
                            }
                        },
                        "required": ["step_number", "description", "reasoning"]
                    }
                }
            },
            "required": ["steps"]
        }
        
        result = await self.llm.structured_generate(
            prompt=reasoning_prompt,
            output_schema=output_schema,
            system_message=system_message
        )
        
        return result.get("steps", [])