"""
LangGraph API Export Module
This module exports the compiled graph for LangGraph API server
"""

from workflow.graph import MVPWorkflowGraph
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the workflow graph
workflow = MVPWorkflowGraph()

# Export the compiled graph for LangGraph API
graph = workflow.app

# Optional: Create an assistant ID for the API
assistant_id = "multimodal-rag-assistant"

# Configuration for the graph
config = {
    "configurable": {
        "thread_id": "default",
        "assistant_id": assistant_id
    }
}