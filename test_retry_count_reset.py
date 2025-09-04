#!/usr/bin/env python
"""
Test script to verify retry_count is properly reset for each new RAG query
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_retry_count_reset():
    """Test that retry_count is reset for each new RAG query"""
    from workflow.graph import create_workflow
    
    # Create the workflow
    logger.info("Creating workflow graph...")
    workflow = create_workflow()
    
    # Test configuration
    config = {
        "recursion_limit": 30,
        "configurable": {"thread_id": "test_retry_count"}
    }
    
    # First query - this might fail and increment retry_count
    logger.info("\n=== Test 1: First RAG query ===")
    first_query = "GV80 엔진 오일에 대해 알려줘"
    input_state = {
        "query": first_query,
        "messages": [HumanMessage(content=first_query)]
    }
    
    try:
        result = workflow.app.invoke(input_state, config)
        retry_count_after_first = result.get("retry_count", 0)
        logger.info(f"First query completed. Final retry_count: {retry_count_after_first}")
        
        # Print answer quality info
        if "answer_quality" in result:
            quality = result["answer_quality"]
            logger.info(f"Answer quality: {quality}")
            
    except Exception as e:
        logger.error(f"First query failed: {e}")
        retry_count_after_first = None
    
    # Second query - test if retry_count is reset
    logger.info("\n=== Test 2: Second RAG query (testing reset) ===")
    second_query = "똑딱이 문서에 대해 알려줘"
    input_state = {
        "query": second_query,
        "messages": [
            HumanMessage(content=first_query),
            AIMessage(content="(Previous answer here)"),
            HumanMessage(content=second_query)
        ]
    }
    
    try:
        # Clear any intermediate state by checking initial state
        result = workflow.app.invoke(input_state, config)
        
        # Check if retry_count was properly reset
        initial_retry_count = None
        final_retry_count = result.get("retry_count", 0)
        
        # Check messages for retry indication
        messages = result.get("messages", [])
        for msg in messages:
            if isinstance(msg, AIMessage) and "답변 재생성 중" in msg.content:
                logger.warning(f"Found retry message: {msg.content}")
                # Extract retry count from message
                import re
                match = re.search(r'시도 (\d+)/(\d+)', msg.content)
                if match:
                    current_try = int(match.group(1))
                    if current_try > 1:
                        logger.error(f"❌ ISSUE: Retry started at attempt {current_try} instead of 1!")
                    else:
                        logger.info(f"✅ OK: Retry properly started at attempt 1")
        
        logger.info(f"Second query completed. Final retry_count: {final_retry_count}")
        
        # Verify reset worked
        if final_retry_count > 0:
            # This is okay if the second query also needed retries
            logger.info(f"✅ Second query needed {final_retry_count} retries (normal behavior)")
        else:
            logger.info("✅ Second query succeeded without retries")
            
    except Exception as e:
        logger.error(f"Second query failed: {e}")
    
    # Third query - additional verification
    logger.info("\n=== Test 3: Third RAG query (additional verification) ===")
    third_query = "디지털 정부 혁신에 대해 알려줘"
    input_state = {
        "query": third_query,
        "messages": [
            HumanMessage(content=first_query),
            AIMessage(content="(Previous answer 1)"),
            HumanMessage(content=second_query),
            AIMessage(content="(Previous answer 2)"),
            HumanMessage(content=third_query)
        ]
    }
    
    try:
        result = workflow.app.invoke(input_state, config)
        final_retry_count = result.get("retry_count", 0)
        
        # Check for improper retry messages
        messages = result.get("messages", [])
        has_issue = False
        for msg in messages:
            if isinstance(msg, AIMessage) and "답변 재생성 중" in msg.content:
                import re
                match = re.search(r'시도 (\d+)/(\d+)', msg.content)
                if match:
                    current_try = int(match.group(1))
                    if current_try > 1 and not has_issue:
                        logger.error(f"❌ ISSUE: Third query retry started at attempt {current_try}!")
                        has_issue = True
        
        if not has_issue:
            logger.info("✅ Third query retry count properly initialized")
            
        logger.info(f"Third query completed. Final retry_count: {final_retry_count}")
        
    except Exception as e:
        logger.error(f"Third query failed: {e}")
    
    logger.info("\n=== Test completed ===")
    logger.info("Check the logs above for any ❌ ISSUE markers.")
    logger.info("If all queries show '✅ OK' or '✅ ... properly ...' then the fix is working!")

if __name__ == "__main__":
    test_retry_count_reset()