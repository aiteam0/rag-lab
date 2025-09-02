#!/usr/bin/env python
"""
LangGraph API Client Example
Shows how to interact with the multimodal RAG workflow via LangGraph API
"""

import asyncio
import json
from typing import Optional, Dict, Any
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient
import httpx

class MultimodalRAGClient:
    """Client for interacting with the Multimodal RAG LangGraph API"""
    
    def __init__(self, base_url: str = "http://localhost:2024"):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the LangGraph API server
        """
        self.base_url = base_url
        self.client: Optional[LangGraphClient] = None
        self.assistant_id = "multimodal-rag"
        
    async def connect(self):
        """Connect to the LangGraph API server"""
        self.client = get_client(url=self.base_url)
        print(f"✅ Connected to LangGraph API at {self.base_url}")
        
        # Search for available assistants
        try:
            assistants = await self.client.assistants.search()
            print(f"📋 Available assistants: {[a['assistant_id'] for a in assistants]}")
        except Exception as e:
            print(f"⚠️  Could not list assistants: {e}")
        
    async def create_thread(self) -> str:
        """
        Create a new conversation thread
        
        Returns:
            Thread ID
        """
        thread = await self.client.threads.create()
        thread_id = thread["thread_id"]
        print(f"🧵 Created thread: {thread_id}")
        return thread_id
        
    async def send_query(
        self, 
        query: str, 
        thread_id: Optional[str] = None,
        stream: bool = True
    ) -> Dict[str, Any]:
        """
        Send a query to the RAG system
        
        Args:
            query: User query
            thread_id: Thread ID (creates new if not provided)
            stream: Whether to stream the response
            
        Returns:
            Response from the system
        """
        if not self.client:
            await self.connect()
            
        # Create thread if not provided
        if not thread_id:
            thread_id = await self.create_thread()
            
        # Prepare the input
        input_data = {
            "query": query,
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": []
        }
        
        print(f"\n🔍 Query: {query}")
        print("-" * 50)
        
        if stream:
            # Stream the response
            result = {}
            async for chunk in self.client.runs.stream(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                input=input_data,
                stream_mode="values"
            ):
                # Process streaming chunks
                if chunk.event == "values":
                    result = chunk.data
                    
                    # Show progress
                    if "current_node" in result:
                        print(f"⚙️  Processing: {result['current_node']}")
                    
                    # Show intermediate results
                    if "intermediate_answer" in result and result["intermediate_answer"]:
                        print(f"💭 Intermediate: {result['intermediate_answer'][:100]}...")
                        
            # Get final answer
            if "final_answer" in result:
                print(f"\n✅ Final Answer:")
                print("-" * 50)
                print(result["final_answer"])
                
            return result
        else:
            # Non-streaming response
            run = await self.client.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                input=input_data
            )
            
            # Wait for completion
            final_state = await self.client.runs.wait(
                thread_id=thread_id,
                run_id=run["run_id"]
            )
            
            if "final_answer" in final_state:
                print(f"\n✅ Final Answer:")
                print("-" * 50)
                print(final_state["final_answer"])
                
            return final_state
            
    async def get_thread_history(self, thread_id: str) -> list:
        """
        Get the conversation history for a thread
        
        Args:
            thread_id: Thread ID
            
        Returns:
            List of states in the thread
        """
        history = []
        async for state in self.client.threads.get_history(thread_id):
            history.append(state)
        return history
        
    async def list_threads(self) -> list:
        """
        List all available threads
        
        Returns:
            List of thread IDs
        """
        threads = await self.client.threads.list()
        return [t["thread_id"] for t in threads]


async def main():
    """Example usage of the client"""
    
    # Initialize client
    client = MultimodalRAGClient()
    await client.connect()
    
    # Example queries
    queries = [
        "GV80의 엔진 오일 교체 주기는 어떻게 되나요?",
        "What are the safety features of the vehicle?",
        "디지털정부혁신의 주요 목표는 무엇인가요?"
    ]
    
    print("\n" + "=" * 60)
    print("🚀 Multimodal RAG API Client Demo")
    print("=" * 60)
    
    # Create a thread for conversation
    thread_id = await client.create_thread()
    
    # Send queries
    for query in queries[:1]:  # Test with first query
        print(f"\n{'='*60}")
        result = await client.send_query(
            query=query,
            thread_id=thread_id,
            stream=True
        )
        
        # Show some statistics
        if "documents" in result:
            print(f"\n📊 Statistics:")
            print(f"  - Documents retrieved: {len(result['documents'])}")
        if "subtasks" in result:
            print(f"  - Subtasks created: {len(result['subtasks'])}")
        if "confidence_score" in result:
            print(f"  - Confidence score: {result['confidence_score']:.2f}")
            
        print("\n" + "=" * 60)
        
        # Wait before next query
        await asyncio.sleep(2)
    
    # Show thread history
    print("\n📜 Thread History:")
    history = await client.get_thread_history(thread_id)
    print(f"  - Total states: {len(history)}")
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())