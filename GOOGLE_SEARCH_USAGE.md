# Google Search Tool Usage Guide
*Implementation Completed: 2025-01-09*

## ✅ Implementation Status
All components successfully implemented and tested!

## 🚀 Quick Start

### Switching Between Search Tools
Edit `.env` file:
```bash
# To use Google Search
USE_GOOGLE_SEARCH=true

# To use Tavily Search (default)
USE_GOOGLE_SEARCH=false
```

## 📊 Test Results
```
✓ All 6 tests passed
✓ Google API connection successful
✓ Quota management working (100 queries/day)
✓ Caching operational (50% hit rate in tests)
✓ Factory pattern switching correctly
✓ Workflow integration verified
```

## 📁 Files Created/Modified

### New Files
- `workflow/tools/google_search.py` - Google Search Tool implementation
- `workflow/tools/tavily_search.py.backup` - Original Tavily backup
- `scripts/test_google_search.py` - Comprehensive test suite
- `GOOGLE_SEARCH_IMPLEMENTATION_PLAN.md` - Implementation plan
- `GOOGLE_SEARCH_USAGE.md` - This usage guide

### Modified Files
- `workflow/tools/__init__.py` - Added factory pattern
- `workflow/graph.py` - Updated to use factory pattern
- `.env` - Added USE_GOOGLE_SEARCH variable

## 🔧 Configuration

### Environment Variables
```bash
# Google API Credentials (already in .env)
GOOGLE_SEARCH_ENGINE_ID="611194f4de36940c1"
GOOGLE_API_KEY="AIzaSyD4cZSBpj_2BcuVY8O30aB9V9H3n35Nyb4"

# Tool Selection
USE_GOOGLE_SEARCH=false  # Change to true to use Google
```

### API Limits
| Feature | Google | Tavily |
|---------|--------|--------|
| Free Queries/Day | 100 | Unknown |
| Max Results/Query | 10 | Configurable |
| Caching | 1 hour | None |
| Cost | $5/1000 after free | Unknown |

## 🧪 Testing

### Run Complete Test Suite
```bash
python scripts/test_google_search.py
```

### Test Specific Tool
```python
# Test Google directly
from workflow.tools.google_search import GoogleSearchTool
google = GoogleSearchTool(max_results=5)
results = google.search_sync("your query")

# Test factory pattern
from workflow.tools import create_search_tool
tool = create_search_tool(max_results=5)
```

## 📈 Features

### Google Search Tool
- ✅ 100% TavilySearchTool interface compatibility
- ✅ Quota management (100/day tracking)
- ✅ Result caching (1 hour TTL)
- ✅ Graceful error handling
- ✅ Async/sync support
- ✅ Domain filtering (advanced_search)
- ✅ Status monitoring (get_status)

### Factory Pattern Benefits
- ✅ Zero code changes in workflow
- ✅ Automatic fallback to Tavily
- ✅ Easy A/B testing
- ✅ Environment-based switching

## 🔄 Workflow Integration

The search tool is automatically selected based on `USE_GOOGLE_SEARCH`:
```python
# In workflow/graph.py
search_tool = create_search_tool(max_results=3)
# Returns GoogleSearchTool or TavilySearchTool based on env var
```

## 📊 Monitoring

### Check Quota Status
```python
from workflow.tools.google_search import GoogleSearchTool
google = GoogleSearchTool()
status = google.get_status()
print(f"Quota: {status['quota']['remaining']}/{status['quota']['limit']}")
print(f"Cache hit rate: {status['cache']['hit_rate']}")
```

### View Logs
```bash
# Google Search specific logs
grep "GOOGLE" logs/workflow_*.log

# Factory pattern logs
grep "FACTORY" logs/workflow_*.log

# Web search logs (both tools)
grep "WEB_SEARCH" logs/workflow_*.log
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Error: google-api-python-client not found**
   ```bash
   pip install google-api-python-client
   ```

2. **Quota Exhausted (100 queries used)**
   - Wait until next day (resets at midnight)
   - Or switch to Tavily: `USE_GOOGLE_SEARCH=false`

3. **API Key Invalid**
   - Check GOOGLE_API_KEY in .env
   - Verify key is enabled in Google Cloud Console

4. **No Results Returned**
   - Check quota: may be exhausted
   - Verify internet connection
   - Check search query format

## 🔍 Usage Examples

### Simple Query
```python
from workflow.tools.google_search import GoogleSearchTool

tool = GoogleSearchTool(max_results=5)
results = tool.search_sync("Python programming")

for doc in results:
    print(f"Title: {doc.metadata['title']}")
    print(f"URL: {doc.metadata['source']}")
    print(f"Score: {doc.metadata['score']}")
```

### Advanced Search with Domain Filter
```python
# Search only specific domains
results = await tool.advanced_search(
    "machine learning",
    include_domains=["arxiv.org", "papers.nips.cc"],
    exclude_domains=["medium.com"]
)
```

### In Workflow Context
```python
# Automatically uses correct tool based on USE_GOOGLE_SEARCH
from workflow.graph import MVPWorkflowGraph

graph = MVPWorkflowGraph()
# graph.tavily_tool is now either GoogleSearchTool or TavilySearchTool
```

## 🎯 Next Steps

1. **Production Use**:
   - Set `USE_GOOGLE_SEARCH=true` in .env
   - Monitor quota usage
   - Adjust cache TTL if needed

2. **Optimization**:
   - Increase cache TTL for common queries
   - Implement query deduplication
   - Add query preprocessing

3. **Monitoring**:
   - Track daily quota usage
   - Monitor cache hit rates
   - Compare result quality vs Tavily

## 📝 Summary

The Google Search Tool is fully implemented, tested, and ready for production use. Simply set `USE_GOOGLE_SEARCH=true` in your `.env` file to start using it. The implementation maintains 100% backward compatibility, so no other code changes are required.

**Current Status**: Using Tavily (USE_GOOGLE_SEARCH=false)  
**To Switch**: Change to USE_GOOGLE_SEARCH=true in .env