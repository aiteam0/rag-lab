# Google Search Tool Implementation Plan
*Created: 2025-01-09*

## 📋 Executive Summary
Replace TavilySearchTool with GoogleSearchTool while maintaining 100% interface compatibility for seamless integration with existing workflow.

## 🔑 Available Credentials
```bash
GOOGLE_SEARCH_ENGINE_ID = "611194f4de36940c1"   
GOOGLE_API_KEY = "AIzaSyD4cZSBpj_2BcuVY8O30aB9V9H3n35Nyb4"
```

## ⚠️ Key Limitations & Considerations

### API Limits
| Feature | Tavily | Google Custom Search |
|---------|--------|---------------------|
| Free Queries/Day | Not specified | 100 |
| Max Results per Query | Configurable | 10 |
| Total Results per Search | Unlimited | 100 max |
| Cost for Additional | Unknown | $5 per 1000 queries |
| Rate Limiting | None mentioned | Strict |

### Technical Differences
1. **Result Limit**: Google returns max 10 results per API call (vs Tavily's configurable)
2. **Daily Quota**: 100 free queries/day requires careful management
3. **Response Format**: Different JSON structure needs mapping
4. **Pagination**: Use `start` parameter for results beyond first 10

## 📦 Implementation Plan

### 1. File Structure
```
workflow/tools/
├── tavily_search.py.backup    # Renamed original
├── google_search.py           # New implementation
└── __init__.py                # Updated imports
```

### 2. Dependencies to Install
```bash
pip install google-api-python-client==2.108.0
```

### 3. Class Structure Design
```python
class GoogleSearchTool:
    """Google Custom Search Tool - Drop-in replacement for TavilySearchTool"""
    
    def __init__(self, max_results: int = 5):
        # Initialize Google API client
        # Load credentials from environment
        # Set up rate limiting
        # Initialize cache
        
    def _search_sync(self, query: str, search_depth: str = "basic") -> Dict:
        # Core Google API search implementation
        # Handle pagination if max_results > 10
        # Map search_depth to num parameter
        
    async def search(self, query: str, search_depth: str = "basic") -> List[Document]:
        # Async wrapper using ThreadPoolExecutor
        # Convert Google results to Document format
        # Maintain exact metadata structure
        
    def search_sync(self, query: str, search_depth: str = "basic") -> List[Document]:
        # Synchronous public interface
        # Cache results to minimize API calls
        
    def as_tool(self) -> Tool:
        # LangChain tool conversion
        # Identical to Tavily implementation
        
    async def advanced_search(self, query: str, 
                            include_domains: List[str] = None,
                            exclude_domains: List[str] = None) -> List[Document]:
        # Use siteSearch and siteSearchFilter parameters
        
    def check_availability(self) -> bool:
        # Verify API credentials and quota
        # Check remaining daily queries
```

### 4. Method Mapping Strategy

#### Core Search Parameters
```python
# Tavily → Google mapping
search_depth_mapping = {
    "basic": {"num": 5},
    "advanced": {"num": 10}
}

# Handle max_results > 10
if max_results > 10:
    # Multiple API calls with pagination
    for start_index in range(0, max_results, 10):
        params['start'] = start_index + 1
        params['num'] = min(10, max_results - start_index)
```

#### Document Conversion
```python
def _convert_to_document(self, google_result: Dict, rank: int, query: str) -> Document:
    """Convert Google result to LangChain Document"""
    
    # Extract fields
    title = google_result.get('title', '')
    snippet = google_result.get('snippet', '')
    link = google_result.get('link', '')
    
    # Format content (identical to Tavily)
    content = f"**{title}**\n\n{snippet}" if title else snippet
    
    # Build metadata (exact same structure)
    metadata = {
        "source": link,
        "title": title,
        "score": 1.0 - (rank * 0.1),  # Simulated score based on rank
        "published_date": google_result.get('pagemap', {})
                         .get('metatags', [{}])[0]
                         .get('article:published_time', ''),
        "search_query": query,
        "search_rank": rank,
        "search_tool": "google"  # Changed from "tavily"
    }
    
    return Document(page_content=content, metadata=metadata)
```

### 5. Error Handling & Rate Limiting

#### Quota Management
```python
class QuotaManager:
    def __init__(self, daily_limit=100):
        self.daily_limit = daily_limit
        self.queries_today = 0
        self.last_reset = datetime.now().date()
        
    def can_query(self) -> bool:
        self._check_reset()
        return self.queries_today < self.daily_limit
        
    def increment(self):
        self.queries_today += 1
        
    def _check_reset(self):
        if datetime.now().date() > self.last_reset:
            self.queries_today = 0
            self.last_reset = datetime.now().date()
```

#### Error Handling
```python
try:
    service = build("customsearch", "v1", developerKey=api_key)
    result = service.cse().list(q=query, cx=cse_id, **params).execute()
except HttpError as e:
    if e.resp.status == 429:  # Rate limit
        logger.warning("Google Search API rate limit reached")
    elif e.resp.status == 403:  # Quota exceeded
        logger.warning("Google Search API daily quota exceeded")
    return {"results": [], "error": str(e)}
except Exception as e:
    return {"results": [], "error": str(e)}
```

### 6. Caching Strategy
```python
class SearchCache:
    def __init__(self, ttl=3600):  # 1 hour TTL
        self.cache = {}
        self.ttl = ttl
        
    def get(self, query: str) -> Optional[List[Document]]:
        if query in self.cache:
            entry_time, documents = self.cache[query]
            if time.time() - entry_time < self.ttl:
                return documents
        return None
        
    def set(self, query: str, documents: List[Document]):
        self.cache[query] = (time.time(), documents)
```

## 🔄 Migration Strategy

### Phase 1: Backup & Preparation
```bash
# Backup original
cp workflow/tools/tavily_search.py workflow/tools/tavily_search.py.backup

# Install dependencies
pip install google-api-python-client
```

### Phase 2: Environment Configuration
```bash
# Add to .env
USE_GOOGLE_SEARCH=false  # Start with false for testing

# Existing Google credentials already present
GOOGLE_SEARCH_ENGINE_ID="611194f4de36940c1"
GOOGLE_API_KEY="AIzaSyD4cZSBpj_2BcuVY8O30aB9V9H3n35Nyb4"
```

### Phase 3: Factory Pattern Implementation
```python
# workflow/tools/__init__.py
def create_search_tool(max_results: int = 5) -> Tool:
    """Factory function to create appropriate search tool"""
    use_google = os.getenv("USE_GOOGLE_SEARCH", "false").lower() == "true"
    
    if use_google:
        try:
            from workflow.tools.google_search import GoogleSearchTool
            tool = GoogleSearchTool(max_results=max_results)
            if tool.check_availability():
                return tool.as_tool()
        except Exception as e:
            logger.warning(f"Google Search initialization failed: {e}")
    
    # Fallback to Tavily
    try:
        from workflow.tools.tavily_search import TavilySearchTool
        return TavilySearchTool(max_results=max_results).as_tool()
    except:
        # Return dummy tool
        return create_dummy_search_tool()
```

### Phase 4: Workflow Integration Update
```python
# workflow/graph.py modification
from workflow.tools import create_search_tool

class MVPWorkflowGraph:
    def __init__(self, checkpointer_path: Optional[str] = None):
        # Replace direct TavilySearchTool initialization
        try:
            search_tool = create_search_tool(max_results=3)
            if hasattr(search_tool, '_raw_tool'):
                # Extract the actual tool instance
                self.search_tool = search_tool._raw_tool
            else:
                self.search_tool = None
            self.use_search = self.search_tool is not None
        except Exception as e:
            print(f"Warning: Search tool initialization failed: {e}")
            self.search_tool = None
            self.use_search = False
```

## ✅ Testing Plan

### 1. Unit Tests
```python
# test_google_search.py
def test_interface_compatibility():
    """Ensure GoogleSearchTool has same interface as TavilySearchTool"""
    
def test_document_format():
    """Verify Document metadata structure matches exactly"""
    
def test_rate_limiting():
    """Test quota management and error handling"""
    
def test_pagination():
    """Test handling of max_results > 10"""
```

### 2. Integration Tests
```bash
# Test with Google disabled (should use Tavily)
USE_GOOGLE_SEARCH=false python scripts/test_web_search_node.py

# Test with Google enabled
USE_GOOGLE_SEARCH=true python scripts/test_web_search_node.py

# Compare results
diff google_results.json tavily_results.json
```

### 3. A/B Testing
```python
# Run both tools and compare
tavily_results = tavily_tool.search_sync(query)
google_results = google_tool.search_sync(query)

# Compare relevance, speed, coverage
compare_search_tools(tavily_results, google_results)
```

## 🎯 Success Criteria

1. **Interface Compatibility**: ✓ All methods match TavilySearchTool signature
2. **Document Format**: ✓ Metadata structure identical
3. **Error Handling**: ✓ Graceful degradation on failures
4. **Performance**: ✓ Caching reduces API calls by >50%
5. **Rate Limiting**: ✓ Stays within 100 queries/day limit
6. **Workflow Integration**: ✓ No changes needed in graph.py logic
7. **Fallback**: ✓ Automatic fallback to Tavily if Google fails

## 📊 Monitoring & Optimization

### Metrics to Track
- Daily query count vs limit
- Cache hit rate
- Average response time
- Error rate by type
- Result relevance comparison

### Optimization Opportunities
1. **Smart Caching**: Cache popular queries longer
2. **Query Batching**: Combine similar queries
3. **Selective Activation**: Only use for certain query types
4. **Hybrid Approach**: Use Google for recent info, local for historical

## 🚨 Rollback Plan

If issues arise:
```bash
# 1. Quick disable via environment
export USE_GOOGLE_SEARCH=false

# 2. Full rollback if needed
mv workflow/tools/tavily_search.py.backup workflow/tools/tavily_search.py
rm workflow/tools/google_search.py

# 3. Restart service
python langgraph_server.py
```

## 📝 Next Steps

1. **Review this plan** and confirm approach
2. **Create google_search.py** with full implementation
3. **Write comprehensive tests**
4. **Gradual rollout** with monitoring
5. **Optimize based on usage patterns**

---

*Note: This plan ensures zero disruption to existing workflow while providing flexibility to switch between search providers.*