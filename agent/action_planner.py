# agent/action_planner.py
from typing import Dict, Any, List, Optional
from agent.llm import LLMService
from agent.reasoning import ChainOfThoughtReasoner
import json
from utils.time_utils import TimeConverter

class Action:
    """Represents a single action to perform"""
    
    def __init__(self, service: str, method: str, params: Dict[str, Any]):
        self.service = service
        self.method = method
        self.params = params
        
class ActionPlan:
    """Represents a plan of actions to execute"""
    
    def __init__(self, 
                actions: List[Action], 
                summary: str, 
                requires_verification: bool = False):
        self.actions = actions
        self.summary = summary
        self.requires_verification = requires_verification

class ActionPlanner:
    """Plans and coordinates actions based on reasoning"""
    
    def __init__(self, 
                llm_service: LLMService, 
                reasoner: ChainOfThoughtReasoner, 
                available_services: Dict[str, Any]):
        self.llm = llm_service
        self.reasoner = reasoner
        self.available_services = available_services
        
    async def plan(self, 
                  intent: Dict[str, Any], 
                  reasoning: List[Dict[str, Any]]) -> ActionPlan:
        """
        Create an action plan based on user intent and reasoning
        
        Args:
            intent: Parsed intent from user message
            reasoning: Chain-of-thought reasoning steps
            
        Returns:
            An action plan to execute
        """
        # Extract required services from reasoning
        required_services = set()
        for step in reasoning:
            if "required_services" in step:
                required_services.update(step["required_services"])
        
        # Format reasoning for the prompt
        reasoning_text = "\n".join([
            f"Step {step['step_number']}: {step['description']}\n"
            f"  Reasoning: {step['reasoning']}"
            for step in reasoning
        ])
        
        # Process ISO timestamps if available
        if "entities" in intent and "start_time_iso" in intent["entities"]:
            intent["entities"]["start_time"] = intent["entities"]["start_time_iso"]
            intent["entities"]["end_time"] = intent["entities"]["end_time_iso"]
        
        system_message = """
        You are an AI assistant that converts reasoning steps into concrete actions.
        For each required service, determine what specific API method to call and what parameters to pass.
        Focus only on email and calendar services.
        """
        
        planning_prompt = f"""
        User intent: {json.dumps(intent, indent=2)}
        
        Reasoning steps:
        {reasoning_text}
        
        Available services: {list(self.available_services.keys())}
        
        For email service, available methods are:
        - send_email (params: to, subject, body)
        - list_emails (params: folder, limit)
        - search_emails (params: query, folder, limit)
        - reply_to_email (params: email_id, body, folder)
        
        For calendar service, available methods are:
        - list_events (params: time_min, time_max, max_results)
        - create_event (params: summary, start_time, end_time, description, location)
        - update_event (params: event_id, summary, start_time, end_time, description, location)
        - delete_event (params: event_id)
        
        Create a concrete action plan with specific methods and parameters.
        Determine if user verification is required before executing (e.g., for sending emails or creating/updating calendar events).
        """
        
        output_schema = {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "description": "List of actions to execute",
                    "items": {
                        "type": "object",
                        "properties": {
                            "service": {"type": "string", "enum": ["email", "calendar"]},
                            "method": {"type": "string"},
                            "params": {"type": "object"}
                        },
                        "required": ["service", "method", "params"]
                    }
                },
                "summary": {"type": "string"},
                "requires_verification": {"type": "boolean"}
            },
            "required": ["actions", "summary", "requires_verification"]
        }
        
        result = await self.llm.structured_generate(
            prompt=planning_prompt,
            output_schema=output_schema,
            system_message=system_message
        )
        
        # Convert to ActionPlan object
        actions = []
        for action_data in result.get("actions", []):
            action = Action(
                service=action_data.get("service"),
                method=action_data.get("method"),
                params=action_data.get("params", {})
            )
            actions.append(action)
        
        # Get the summary and verification requirement from the result
        summary = result.get("summary", "")
        requires_verification = result.get("requires_verification", False)
        
        # Validate calendar actions for conflicts if there are calendar actions
        calendar_actions = [a for a in actions if a.service == "calendar"]
        if calendar_actions:
            validation_result = await self.validate_calendar_actions(actions)
            
            # If conflicts found, mark plan as requiring verification
            if not validation_result["valid"]:
                requires_verification = True
                
                # Add conflict information to the summary
                conflict_details = "\n\nPotential conflicts detected:\n"
                for conflict in validation_result["conflicts"]:
                    conflict_events = conflict.get("conflicts", [])
                    conflict_details += f"- {conflict['message']}:\n"
                    
                    for evt in conflict_events:
                        evt_summary = evt.get("summary", "Untitled event")
                        evt_start = evt.get("start", "Unknown time")
                        conflict_details += f"  • {evt_summary} at {evt_start}\n"
                
                summary += conflict_details
            
        return ActionPlan(
            actions=actions,
            summary=summary,
            requires_verification=requires_verification
        )
    
    async def validate_calendar_actions(self, actions: List[Action]) -> Dict[str, Any]:
        """
        Validate calendar actions for potential conflicts
        
        Args:
            actions: List of actions to validate
            
        Returns:
            Dictionary with validation results and potential issues
        """
        validated_actions = []
        conflicts = []
        
        # Get calendar service if available
        calendar_service = self.available_services.get("calendar")
        if not calendar_service:
            return {
                "valid": True,
                "actions": actions,
                "conflicts": [],
                "message": "No calendar service available to check conflicts"
            }
        
        # Check each action for potential conflicts
        for action in actions:
            if action.service == "calendar" and action.method == "create_event":
                # Extract event details
                start_time = action.params.get("start_time")
                end_time = action.params.get("end_time")
                summary = action.params.get("summary", "Untitled Event")
                
                # Make sure times are in proper ISO format with timezone
                if start_time and end_time:
                    start_time, end_time = calendar_service._ensure_iso_format(start_time, end_time)
                    action.params["start_time"] = start_time
                    action.params["end_time"] = end_time
                
                if start_time and end_time:
                    # Check for conflicts
                    conflict_result = await calendar_service.check_conflicts(
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if conflict_result.get("status") == "success" and conflict_result.get("has_conflicts", False):
                        conflict_events = conflict_result.get("conflicts", [])
                        conflicts.append({
                            "action": action,
                            "conflicts": conflict_events,
                            "message": f"Event '{summary}' conflicts with {len(conflict_events)} existing events"
                        })
                    else:
                        validated_actions.append(action)
                else:
                    # Can't check conflicts without times
                    validated_actions.append(action)
            else:
                # Non-calendar or non-create actions don't need conflict checking
                validated_actions.append(action)
        
        # Return validation results
        return {
            "valid": len(conflicts) == 0,
            "actions": validated_actions if len(conflicts) == 0 else actions,
            "conflicts": conflicts,
            "message": f"Found {len(conflicts)} potential conflicts" if conflicts else "No conflicts found"
        }
        
    async def generate_response(self, 
                              action_plan: ActionPlan,
                              results: List[Dict[str, Any]]) -> str:
        """Generate a user-friendly response based on execution results"""
        # Check for conflict results specifically
        conflict_results = [r for r in results if r.get("status") == "conflict"]
        if conflict_results:
            return await self.generate_response_with_conflicts(action_plan, results)
        
        prompt = f"""
        I executed the following action plan:
        {action_plan.summary}
        
        Here are the execution results:
        {json.dumps(results, indent=2)}
        
        Generate a helpful, friendly response for the user that explains what was done
        and summarizes the results in a natural way. Be specific about what was achieved.
        If there were any errors, explain what went wrong in simple terms.
        Format the response appropriately for WhatsApp (using *bold* for emphasis where useful).
        """
        
        response = await self.llm.generate(prompt=prompt)
        return response
    
    async def generate_response_with_conflicts(self, 
                                         action_plan: ActionPlan,
                                         results: List[Dict[str, Any]]) -> str:
        """Generate a user-friendly response based on execution results with conflict handling"""
        
        # Check for conflict results specifically
        conflict_results = [r for r in results if r.get("status") == "conflict"]
        if conflict_results:
            # Get the conflicts from the first conflict result
            first_conflict = conflict_results[0]
            conflicts = first_conflict.get("conflicts", [])
            
            # Generate alternative time suggestions if possible
            alternatives_text = ""
            
            if len(conflicts) > 0 and "start_time" in action_plan.actions[0].params:
                start_time = action_plan.actions[0].params["start_time"]
                end_time = action_plan.actions[0].params["end_time"]
                
                # Get alternative suggestions
                alternatives = TimeConverter.get_alternate_time_suggestions(start_time, end_time, conflicts)
                
                if alternatives:
                    alternatives_text = "\n\nHere are some alternative times I could suggest:\n"
                    for i, (alt_start, alt_end) in enumerate(alternatives[:3], 1):
                        # Format as human-readable time
                        time_range = TimeConverter.format_time_range(alt_start, alt_end)
                        alternatives_text += f"{i}. {time_range}\n"
            
            conflict_prompt = f"""
            I attempted to execute the following action plan:
            {action_plan.summary}
            
            However, I found calendar conflicts:
            {json.dumps(conflict_results, indent=2)}
            
            {alternatives_text}
            
            Generate a helpful, friendly response for the user that explains:
            1. What conflicts were found (be specific about the conflicting events)
            2. Suggest specific alternative times when the event could be scheduled (use the alternatives provided if available)
            3. Ask if the user would like to:
               a) Reschedule to one of your suggested times
               b) Override and create a conflicting event anyway
               c) Cancel the event creation
            
            Format the response appropriately for WhatsApp (using *bold* for emphasis where useful).
            """
            
            response = await self.llm.generate(prompt=conflict_prompt)
            return response
        
        # Use the standard response generation for non-conflict cases
        prompt = f"""
        I executed the following action plan:
        {action_plan.summary}
        
        Here are the execution results:
        {json.dumps(results, indent=2)}
        
        Generate a helpful, friendly response for the user that explains what was done
        and summarizes the results in a natural way. Be specific about what was achieved.
        If there were any errors, explain what went wrong in simple terms.
        Format the response appropriately for WhatsApp (using *bold* for emphasis where useful).
        """
        
        response = await self.llm.generate(prompt=prompt)
        return response
        
    def format_dates_and_times(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Format dates and times from natural language to ISO format"""
        # This would be implemented to convert natural language dates and times
        # into ISO format for API calls. For now, we'll return the original intent.
        return intent
        
    def validate_required_parameters(self, action: Action) -> bool:
        """Check if all required parameters for an action are present"""
        if action.service == "email":
            if action.method == "send_email":
                return "to" in action.params and "subject" in action.params
            elif action.method == "reply_to_email":
                return "email_id" in action.params and "body" in action.params
        elif action.service == "calendar":
            if action.method == "create_event":
                return "summary" in action.params and "start_time" in action.params and "end_time" in action.params
            elif action.method == "update_event":
                return "event_id" in action.params
            elif action.method == "delete_event":
                return "event_id" in action.params
        return True