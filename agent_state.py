# agent_state.py
from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """
    Represents the state of our email processing agent.
    This state is passed between nodes in the LangGraph.
    """
    # Raw emails fetched from Gmail
    emails_to_process: List[Dict[str, Any]]
    # The current email being processed by the LLM
    current_email: Optional[Dict[str, Any]]
    # The LLM's output for the current email
    llm_output: Optional[Dict[str, Any]]
    # List of emails that have been processed with their summaries/categories
    processed_emails_results: List[Dict[str, Any]]
    # Index to keep track of which email is currently being processed
    email_index: int