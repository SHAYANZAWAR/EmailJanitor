# email_agent.py (update this existing file)
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from langgraph.graph import StateGraph, END, START
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from agent_state import AgentState 
# Import your utilities
from gmail_utils import get_gmail_service, get_emails, mark_email_as_read, apply_label_to_email
from db_utils import init_db, add_processed_email_id, check_if_email_processed # New Import


# --- Global Configurations ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please set it.")
genai.configure(api_key=GOOGLE_API_KEY)
MODEL_NAME = 'gemini-2.5-flash' 
llm = genai.GenerativeModel(MODEL_NAME)

# --- Ensure DB is initialized when agent starts ---
init_db() # Call this once when the script loads

# --- LangGraph Nodes ---

def fetch_emails_node(state: AgentState) -> AgentState:
    """
    Node to fetch emails of the current day from Gmail and filter out processed ones.
    """
    print("--- Node: Fetching & Filtering Emails ---")
    service = get_gmail_service()
    if not service:
        print("Error: Could not get Gmail service. Cannot fetch emails.")
        return state

    # 1. Query emails of the current day
    today_date_str = datetime.now().strftime("%Y/%m/%d")
    print(f"Fetching unread emails from after: {today_date_str}...")
    
    # Fetch all unread emails from today onwards (max_results set higher to allow filtering)
    fetched_emails = get_emails(service, query="is:unread", date_after=today_date_str)
    
    unprocessed_emails = []
    if fetched_emails:
        for email in fetched_emails:
            # 2. Only process emails that have not been processed
            if not check_if_email_processed(email['id']):
                unprocessed_emails.append(email)
            else:
                print(f"Email '{email['subject']}' (ID: {email['id']}) already processed. Skipping.")
    
    if not unprocessed_emails:
        print("No new, unprocessed emails found for today.")
        return {
            "emails_to_process": [],
            "current_email": None,
            "email_index": 0,
            "processed_emails_results": state.get("processed_emails_results", [])
        }

    print(f"Found {len(unprocessed_emails)} new, unprocessed emails from today.")
    return {
        "emails_to_process": unprocessed_emails,
        "current_email": unprocessed_emails[0], # Start with the first unprocessed email
        "email_index": 0,
        "processed_emails_results": state.get("processed_emails_results", [])
    }

def process_with_llm_node(state: AgentState) -> AgentState:
    """
    Node to process the current email with the LLM (Gemini), without summarization.
    """
    print("--- Node: Processing with LLM (Categorization & Action Items Only) ---")
    current_email = state.get("current_email")
    if not current_email:
        print("Error: No current email to process with LLM.")
        return state

    email_subject = current_email.get('subject', 'No Subject')
    email_body = current_email.get('body', 'No Body')

    # 3. Remove the summary part for now
    prompt = f"""
    You are an intelligent email categorization agent.
    Analyze the following email and provide:
    1. A category from the following list:
       - Urgent/Action Required
       - Information/Read Only
       - Meeting/Appointment
       - Personal/Social
       - Promotions/Offers
       - Support/Troubleshooting
       - Project/Work Related
       - Spam/Junk
       - Other (specify briefly if possible)
    2. Any clear action items for the recipient, listed clearly as a Python list of strings. If none, state "None."

    Format your output as a JSON object with the following keys:
    {{
        "category": "...",
        "action_items": ["...", "..."]
    }}

    --- Email Subject ---
    {email_subject}

    --- Email Body ---
    {email_body}
    """
    
    try:
        response = llm.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        parsed_response = json.loads(response.text)
        print(f"LLM Output for '{email_subject}': Category: {parsed_response.get('category', 'N/A')}")
        
        # Ensure action_items is a list, even if LLM returned "None" or a string
        action_items = parsed_response.get('action_items', [])
        if isinstance(action_items, str) and action_items.lower() == 'none':
            action_items = []
        elif isinstance(action_items, str): # If LLM returns a single string like "check status", convert to list
            action_items = [action_items]


        return {
            "llm_output": {
                "category": parsed_response.get('category'),
                "action_items": action_items
            },
            "processed_emails_results": state.get("processed_emails_results", []) + [{
                "email_id": current_email['id'],
                "subject": email_subject,
                "category": parsed_response.get('category'),
                "action_items": action_items
            }]
        }
        
    except Exception as e:
        print(f"Error processing email with LLM for '{email_subject}': {e}")
        return {
            "llm_output": {
                "category": "Other",
                "action_items": []
            },
            "processed_emails_results": state.get("processed_emails_results", []) + [{
                "email_id": current_email['id'],
                "subject": email_subject,
                "category": "Other",
                "action_items": []
            }]
        }

def update_gmail_node(state: AgentState) -> AgentState:
    """
    Node to update Gmail based on LLM output (apply label, mark as read)
    and mark email as processed in local DB.
    """
    print("--- Node: Updating Gmail & Marking Processed ---")
    current_email = state.get("current_email")
    llm_output = state.get("llm_output")
    
    if not current_email or not llm_output:
        print("Error: No email or LLM output to update Gmail with.")
        return state

    service = get_gmail_service()
    if not service:
        print("Error: Could not get Gmail service. Cannot update email.")
        return state

    email_id = current_email['id']
    category = llm_output.get('category', 'Other')

    # Apply the category as a label
    apply_label_to_email(service, email_id, category)

    # Mark the email as read
    mark_email_as_read(service, email_id)
    
    # 2. Mark the email as processed in our local database
    add_processed_email_id(email_id)
    print(f"Email ID: {email_id} marked as processed in DB.")
    
    return state

def prepare_next_email_node(state: AgentState) -> AgentState:
    """
    Node to advance to the next email in the list.
    """
    print("--- Node: Preparing Next Email ---")
    emails_to_process = state.get("emails_to_process", [])
    current_index = state.get("email_index", 0)

    next_index = current_index + 1

    if next_index < len(emails_to_process):
        return {
            "current_email": emails_to_process[next_index],
            "email_index": next_index
        }
    else:
        return {
            "current_email": None,
            "email_index": next_index
        }

# --- Conditional Edge Function ---

def should_continue(state: AgentState) -> str:
    """
    Conditional logic to determine if more emails need processing.
    """
    print("--- Conditional Node: Checking if more emails ---")
    if state.get("current_email") is None:
        print("No more emails to process. Ending graph.")
        return "end"
    else:
        print(f"More emails to process (current index: {state.get('email_index')}). Continuing.")
        return "continue"

# --- Build the LangGraph ---

def build_email_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("fetch_emails", fetch_emails_node)
    workflow.add_node("process_with_llm", process_with_llm_node)
    workflow.add_node("update_gmail", update_gmail_node)
    workflow.add_node("prepare_next_email", prepare_next_email_node)

    workflow.set_entry_point("fetch_emails")

    workflow.add_edge("fetch_emails", "process_with_llm") 
    
    workflow.add_edge("process_with_llm", "update_gmail")

    workflow.add_conditional_edges(
        "update_gmail",
        should_continue,
        {
            "continue": "prepare_next_email",
            "end": END
        }
    )

    workflow.add_edge("prepare_next_email", "process_with_llm")

    app = workflow.compile()
    return app

# --- Main execution function ---
if __name__ == "__main__":
    agent_app = build_email_agent_graph()

    initial_state = {
        "emails_to_process": [],
        "current_email": None,
        "llm_output": None,
        "processed_emails_results": [],
        "email_index": 0
    }

    print("Starting Email Summarizer Agent...")
    for s in agent_app.stream(initial_state):
        # We can print current state for debugging, but it can be verbose
        # print(f"Current State: {s}")
        # print("---")
        pass # Suppress verbose state printing during stream

    # After the graph finishes, print all processed results
    final_state = agent_app.invoke(initial_state) # Re-run to get final state efficiently
    print("\n--- Agent Run Completed ---")
    print("Summary of all processed emails:")
    for result in final_state.get("processed_emails_results", []):
        print(f"\nSubject: {result['subject']}")
        # print(f"Summary: {result['summary']}") # Summary removed
        print(f"Category: {result['category']}")
        print(f"Action Items: {', '.join(result['action_items']) if result['action_items'] else 'None'}")