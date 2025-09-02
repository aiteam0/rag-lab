# LangGraph API Server Guide

## 🚀 Quick Start

This project is configured to run as a LangGraph API server, exposing the multimodal RAG workflow through a REST API.

## 📋 Prerequisites

All dependencies are already installed via `uv`:
- ✅ langgraph-cli
- ✅ langgraph-sdk
- ✅ uvicorn
- ✅ fastapi

## 🏃 Running the Server

### Development Mode (with hot reload)
```bash
# Using the server script
uv run python langgraph_server.py

# Or directly with langgraph CLI
uv run langgraph dev --host 127.0.0.1 --port 8123
```

### Production Mode
```bash
# Using the server script (production)
uv run python langgraph_server.py
# Then type: production

# Or directly
uv run langgraph up --host 0.0.0.0 --port 8000
```

## 📚 API Endpoints

Once the server is running, you can access:

- **API Documentation**: http://localhost:8123/docs
- **Health Check**: http://localhost:8123/health
- **OpenAPI Schema**: http://localhost:8123/openapi.json

### Core Endpoints

1. **Create Thread**
   ```
   POST /threads
   ```

2. **Run Query**
   ```
   POST /threads/{thread_id}/runs
   Body: {
     "assistant_id": "multimodal-rag",
     "input": {
       "query": "Your question here"
     }
   }
   ```

3. **Stream Response**
   ```
   POST /threads/{thread_id}/runs/stream
   ```

4. **Get Thread History**
   ```
   GET /threads/{thread_id}/history
   ```

## 🧪 Testing the API

### Using the Python Client

```python
# Run the test client
uv run python langgraph_api_client.py
```

### Using cURL

```bash
# 1. Create a thread
THREAD_ID=$(curl -X POST http://localhost:8123/threads \
  -H "Content-Type: application/json" \
  | jq -r '.thread_id')

# 2. Send a query
curl -X POST http://localhost:8123/threads/$THREAD_ID/runs \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "multimodal-rag",
    "input": {
      "query": "GV80의 엔진 오일 교체 주기는?"
    }
  }'
```

### Using httpie

```bash
# Create thread
http POST localhost:8123/threads

# Send query
http POST localhost:8123/threads/{thread_id}/runs \
  assistant_id=multimodal-rag \
  input:='{"query": "What are the safety features?"}'
```

## 🔧 Configuration

### Environment Variables (.env)
```ini
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=admin

# Query Routing
ENABLE_QUERY_ROUTING=true

# LangGraph
LANGGRAPH_PLANNING_MAX_SUBTASKS=5
CRAG_MAX_RETRIES=3
```

### Graph Configuration (langgraph.json)
```json
{
  "graphs": {
    "multimodal-rag": "./api_graph.py:graph"
  },
  "env": ".env"
}
```

## 📊 Workflow Overview

The API exposes a sophisticated RAG pipeline with:

1. **Query Routing**: Intelligent classification (simple/RAG/history)
2. **Planning**: Decomposes queries into 1-5 subtasks
3. **Retrieval**: Dual-language hybrid search
4. **Synthesis**: Structured answer generation
5. **Validation**: CRAG hallucination checking
6. **Quality**: Multi-dimensional answer grading

## 🔍 Monitoring

### Server Logs
The server provides detailed logs showing:
- Query routing decisions
- Subtask execution
- Document retrieval stats
- CRAG validation results
- Performance metrics

### Example Log Output
```
2024-01-10 10:30:15 - INFO - 🚀 Starting LangGraph API Server (dev mode)
2024-01-10 10:30:15 - INFO - 📄 Config: langgraph.json
2024-01-10 10:30:15 - INFO - 🌐 Server: http://127.0.0.1:8123
2024-01-10 10:30:15 - INFO - 📚 API Docs: http://127.0.0.1:8123/docs
```

## 🐳 Docker Deployment (Optional)

Generate a Dockerfile:
```bash
uv run langgraph dockerfile > Dockerfile
```

Build and run:
```bash
docker build -t multimodal-rag-api .
docker run -p 8000:8000 --env-file .env multimodal-rag-api
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Change port in langgraph_server.py
   # Or kill the process using the port
   lsof -i :8123
   kill -9 <PID>
   ```

2. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify .env credentials
   - Ensure pgvector extension is installed

3. **LangGraph CLI Not Found**
   - Always use `uv run` prefix
   - Or activate the virtual environment first

4. **Module Import Errors**
   - Ensure all dependencies are installed: `uv sync`
   - Check Python path includes project root

## 📈 Performance Tips

1. **Enable Query Routing**: Reduces latency by 90% for simple queries
2. **Adjust Subtask Limits**: Lower `LANGGRAPH_PLANNING_MAX_SUBTASKS` for faster responses
3. **Use Streaming**: Better user experience with progressive responses
4. **Cache Threads**: Reuse thread IDs for related queries

## 🔗 Related Documentation

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [LangGraph API Reference](https://python.langchain.com/docs/langgraph/api_reference)
- [Project Architecture](./PROJECT_ARCHITECTURE_DEEP_ANALYSIS.md)