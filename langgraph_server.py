#!/usr/bin/env python
"""
LangGraph API Server
Runs the multimodal RAG workflow as a LangGraph API server
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if all requirements are met"""
    project_root = Path(__file__).parent
    checks = {
        "langgraph.json": (project_root / "langgraph.json").exists(),
        "api_graph.py": (project_root / "api_graph.py").exists(),
        ".env file": (project_root / ".env").exists(),
    }
    
    all_passed = True
    logger.info("🔍 Checking requirements...")
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        logger.info(f"  {status} {name}")
        if not passed:
            all_passed = False
            
    return all_passed

def run_server(
    host: str = "0.0.0.0",
    port: int = 2024,
    mode: str = "dev"
):
    """
    Run the LangGraph API server
    
    Args:
        host: Host to bind to
        port: Port to bind to
        mode: "dev" for development with hot reload, "prod" for production
    """
    config_path = Path(__file__).parent / "langgraph.json"
    
    logger.info(f"🚀 Starting LangGraph API Server ({mode} mode)")
    logger.info(f"📄 Config: {config_path}")
    logger.info(f"🌐 Server: http://{host}:{port}")
    logger.info(f"📚 API Docs: http://{host}:{port}/docs")
    logger.info("-" * 60)
    
    # Build command based on mode (using uv run since langgraph is installed via uv)
    if mode == "dev":
        cmd = ["uv", "run", "langgraph", "dev", "--host", host, "--port", str(port)]
    else:
        cmd = ["uv", "run", "langgraph", "up", "--host", host, "--port", str(port)]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped by user")

def run_dev_server():
    """Run development server with hot reload"""
    if not check_requirements():
        logger.error("❌ Requirements check failed")
        sys.exit(1)
    run_server(host="127.0.0.1", port=2024, mode="dev")

def run_production_server():
    """Run production server"""
    if not check_requirements():
        logger.error("❌ Requirements check failed")
        sys.exit(1)
    run_server(host="0.0.0.0", port=8000, mode="prod")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "production":
        run_production_server()
    else:
        run_dev_server()