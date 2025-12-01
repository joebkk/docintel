# API Reference

Complete API documentation for DocIntel's RAG Backend and Agent System.

## Base URLs

- **RAG Backend**: `http://localhost:3000`
- **Agent System**: `http://localhost:8000`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3001`
- **Jaeger**: `http://localhost:16686`

---

## RAG Backend API

### Search & Retrieval

#### POST /api/unified-search

Perform hybrid document search with AI-generated answers.

**Request**:
\`\`\`json
{
  "query": "What was the Q3 2024 portfolio performance?",
  "mode": "hybrid",           // "lexical" | "semantic" | "hybrid"
  "fileNames": ["Q3_2024_Portfolio_Report.pdf"]  // optional filter
}
\`\`\`

**Response** (Server-Sent Events):
\`\`\`
data: {"type":"metadata","searchMode":"hybrid","resultCount":3}

data: {"type":"sources","sources":[{"fileName":"Q3_2024_Portfolio_Report.pdf","score":1.89}]}

data: {"type":"text","content":"# Q3 2024 Performance\\n\\n"}
data: {"type":"text","content":"The portfolio achieved..."}

data: {"type":"done"}
\`\`\`

**cURL Example**:
\`\`\`bash
curl -X POST http://localhost:3000/api/unified-search \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "portfolio performance Q3 2024",
    "mode": "hybrid"
  }'
\`\`\`

**Response Fields**:
- `metadata`: Search configuration and result count
- `sources`: Ranked document sources with scores
- `text`: Streaming answer chunks
- `done`: End of stream marker

---

#### GET /api/health

Health check endpoint.

**Response**:
\`\`\`json
{
  "status": "ok",
  "timestamp": "2024-12-01T10:30:00.000Z"
}
\`\`\`

---

### Document Processing (Webhook)

#### POST /api/webhooks/document-changes

Trigger document processing workflow (requires authentication).

**Headers**:
\`\`\`
Authorization: Bearer <DOCUMENT_WEBHOOK_API_KEY>
Content-Type: application/json
\`\`\`

**Request (Single Document)**:
\`\`\`json
{
  "documentId": "doc-uuid-123",
  "filename": "NewReport.pdf",
  "operation": "created"  // "created" | "updated"
}
\`\`\`

**Request (Batch)**:
\`\`\`json
{
  "documents": [
    {
      "documentId": "doc-uuid-123",
      "filename": "Report1.pdf",
      "operation": "created"
    },
    {
      "documentId": "doc-uuid-456",
      "filename": "Report2.pdf",
      "operation": "updated"
    }
  ]
}
\`\`\`

**Response**:
\`\`\`json
{
  "status": "accepted",
  "workflowId": "wf-1234567890",
  "documentCount": 2
}
\`\`\`

**Workflow Steps**:
1. Fetch PDF from DigitalOcean Spaces
2. Parse with LlamaParse
3. Generate embeddings (OpenAI)
4. Store in MongoDB (doc_pages, doc_chunks)
5. Update processing state

---

## Agent System API

### Multi-Agent Queries

#### POST /query

Execute multi-agent workflow for complex queries.

**Request**:
\`\`\`json
{
  "query": "What were the Q3 2024 results?",
  "session_id": "user-session-123",  // optional
  "execution_pattern": "sequential",  // "sequential" | "parallel" | "loop"
  "user_id": "user-456"               // optional
}
\`\`\`

**Response**:
\`\`\`json
{
  "workflow_id": "wf_1733061234.567",
  "result": {
    "final_answer": "Q3 2024 showed strong performance with 15% IRR...",
    "sources": [
      {
        "fileName": "Q3_2024_Portfolio_Report.pdf",
        "score": 1.89
      }
    ],
    "research_summary": "...",
    "analysis_insights": {
      "key_metrics": {
        "IRR": "15%",
        "AUM": "$500M",
        "exits": 2
      }
    },
    "citations": [
      {
        "claim": "15% IRR",
        "source": "Q3_2024_Portfolio_Report.pdf",
        "confidence": 0.95
      }
    ]
  },
  "execution_pattern": "sequential",
  "total_tasks": 4,
  "duration_seconds": 12.34,
  "session_id": "user-session-123"
}
\`\`\`

**Execution Patterns**:

- **sequential**: Linear execution (default)
  - Research → Analysis → Citation → Synthesis
  - Best for: Simple queries with dependencies

- **parallel**: Concurrent execution
  - Multiple research queries at once
  - Best for: Multi-document comparisons

- **loop**: Iterative refinement
  - Execute → Evaluate → Refine → Repeat
  - Best for: Complex research requiring multiple passes

**cURL Example**:
\`\`\`bash
curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "Compare Q3 vs Q2 2024 performance",
    "session_id": "test-session",
    "execution_pattern": "parallel"
  }'
\`\`\`

---

#### POST /research

Direct research agent query (bypasses orchestrator).

**Request**:
\`\`\`json
{
  "query": "Q3 2024 IRR",
  "mode": "hybrid",  // "lexical" | "semantic" | "hybrid"
  "file_names": ["Q3_2024_Portfolio_Report.pdf"]  // optional
}
\`\`\`

**Response**:
\`\`\`json
{
  "status": "completed",
  "query": "Q3 2024 IRR",
  "sources": [...],
  "raw_answer": "The Q3 2024 IRR was 15%...",
  "enhanced_summary": "# Q3 2024 IRR Analysis\\n\\n...",
  "key_facts": [
    "Q3 2024 IRR: 15%",
    "Up from 12% in Q2 2024"
  ],
  "information_gaps": [
    "Year-over-year comparison not found"
  ],
  "metadata": {
    "num_sources": 2,
    "search_mode": "hybrid"
  }
}
\`\`\`

---

### Session Management

#### POST /sessions

Create a new session.

**Request**:
\`\`\`json
{
  "user_id": "user-456"  // optional
}
\`\`\`

**Response**:
\`\`\`json
{
  "session_id": "sess-1733061234-abc123",
  "user_id": "user-456",
  "message_count": 0,
  "created_at": "2024-12-01T10:30:00.000Z",
  "updated_at": "2024-12-01T10:30:00.000Z"
}
\`\`\`

---

#### GET /sessions/{session_id}

Get session information.

**Response**:
\`\`\`json
{
  "session_id": "sess-1733061234-abc123",
  "user_id": "user-456",
  "message_count": 4,
  "created_at": "2024-12-01T10:30:00.000Z",
  "updated_at": "2024-12-01T10:35:00.000Z"
}
\`\`\`

---

#### GET /sessions/{session_id}/messages

Get conversation history.

**Query Parameters**:
- `limit` (optional): Max messages to return

**Response**:
\`\`\`json
{
  "session_id": "sess-1733061234-abc123",
  "messages": [
    {
      "role": "user",
      "content": "What was Q3 2024 IRR?",
      "timestamp": "2024-12-01T10:30:00.000Z"
    },
    {
      "role": "assistant",
      "content": "The Q3 2024 IRR was 15%...",
      "timestamp": "2024-12-01T10:30:12.000Z"
    }
  ]
}
\`\`\`

---

#### DELETE /sessions/{session_id}

Delete a session.

**Response**:
\`\`\`json
{
  "status": "deleted",
  "session_id": "sess-1733061234-abc123"
}
\`\`\`

---

### Checkpointing (Human-in-Loop)

#### POST /sessions/{session_id}/checkpoint

Save current session state for later resumption.

**Response**:
\`\`\`json
{
  "status": "checkpoint_created",
  "checkpoint_id": "cp-1733061234-xyz789",
  "session_id": "sess-1733061234-abc123"
}
\`\`\`

---

#### POST /checkpoints/{checkpoint_id}/restore

Restore session from checkpoint.

**Response**:
\`\`\`json
{
  "status": "checkpoint_restored",
  "checkpoint_id": "cp-1733061234-xyz789",
  "session_id": "sess-1733061234-abc123"
}
\`\`\`

**Use Case**:
\`\`\`bash
# Day 1: Start long analysis
curl -X POST http://localhost:8000/sessions \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "user-123"}'

# Process some queries...
curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Analyze first 5 companies", "session_id": "sess-123"}'

# Create checkpoint
curl -X POST http://localhost:8000/sessions/sess-123/checkpoint

# Day 2: Restore and continue
curl -X POST http://localhost:8000/checkpoints/cp-123/restore

# Continue with remaining queries
curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Analyze remaining companies", "session_id": "sess-123"}'
\`\`\`

---

### Memory Bank (Long-Term Memory)

#### POST /memory

Store information in persistent memory.

**Request**:
\`\`\`json
{
  "content": "User prefers detailed financial metrics in responses",
  "memory_type": "preference",  // "fact" | "preference" | "insight"
  "session_id": "sess-123",     // optional
  "user_id": "user-456",        // optional
  "importance": 0.9,            // 0.0-1.0
  "tags": ["preferences", "finance"]
}
\`\`\`

**Response**:
\`\`\`json
{
  "status": "stored",
  "entry_id": "mem-1733061234-abc123",
  "memory_type": "preference"
}
\`\`\`

---

#### GET /memory

Retrieve memories from memory bank.

**Query Parameters**:
- `user_id` (optional): Filter by user
- `session_id` (optional): Filter by session
- `memory_type` (optional): "fact" | "preference" | "insight"
- `min_importance` (optional): Minimum importance score (0.0-1.0)
- `limit` (optional): Max results (default: 10)

**Response**:
\`\`\`json
{
  "count": 3,
  "memories": [
    {
      "entry_id": "mem-1733061234-abc123",
      "content": "User prefers detailed financial metrics",
      "memory_type": "preference",
      "importance": 0.9,
      "created_at": "2024-12-01T10:00:00.000Z",
      "tags": ["preferences", "finance"]
    }
  ]
}
\`\`\`

---

#### GET /memory/stats

Get memory bank statistics.

**Query Parameters**:
- `user_id` (optional): Filter by user

**Response**:
\`\`\`json
{
  "total_memories": 150,
  "by_type": {
    "fact": 80,
    "preference": 45,
    "insight": 25
  },
  "most_accessed": [
    {
      "entry_id": "mem-123",
      "content": "Q3 2024 IRR was 15%",
      "access_count": 12
    }
  ]
}
\`\`\`

---

### Health & Monitoring

#### GET /health

Agent system health check.

**Response**:
\`\`\`json
{
  "status": "healthy",
  "service": "docintel-agents",
  "version": "1.0.0"
}
\`\`\`

---

#### GET /metrics

Prometheus metrics endpoint.

**Response**: Prometheus text format
\`\`\`
# HELP agent_active_sessions Number of active sessions
# TYPE agent_active_sessions gauge
agent_active_sessions 5.0

# HELP agent_workflow_total Total workflows executed
# TYPE agent_workflow_total counter
agent_workflow_total{pattern="sequential"} 120.0
agent_workflow_total{pattern="parallel"} 45.0
agent_workflow_total{pattern="loop"} 12.0

# HELP agent_workflow_duration_seconds Workflow execution time
# TYPE agent_workflow_duration_seconds histogram
agent_workflow_duration_seconds_bucket{le="5.0"} 80.0
agent_workflow_duration_seconds_bucket{le="10.0"} 150.0
agent_workflow_duration_seconds_bucket{le="+Inf"} 177.0

# HELP agent_llm_tokens_total LLM token usage
# TYPE agent_llm_tokens_total counter
agent_llm_tokens_total{model="gemini-2.0-flash-exp",type="input"} 125430.0
agent_llm_tokens_total{model="gemini-2.0-flash-exp",type="output"} 34567.0
\`\`\`

---

## Error Handling

### Error Response Format

All APIs return errors in this format:

\`\`\`json
{
  "error": "Error message",
  "details": "Detailed error description"
}
\`\`\`

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing/invalid auth) |
| 404 | Not Found (session/resource not found) |
| 429 | Too Many Requests (rate limit) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (e.g., MongoDB down) |

---

## Rate Limits

### Gemini API (Agent System)
- **Free Tier**: 10 requests/minute
- **Paid Tier**: Higher limits based on quota

**Handling**:
\`\`\`json
{
  "detail": "429 You exceeded your current quota..."
}
\`\`\`

**Solution**: Wait 60 seconds or upgrade to paid tier

### MongoDB Atlas
- **Free Tier**: 512 MB storage, 100 connections
- **Shared Tier**: Higher limits

---

## SDK Examples

### Python Client

\`\`\`python
import requests

class DocIntelClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def query(self, query: str, session_id: str = None, pattern: str = "sequential"):
        response = requests.post(
            f"{self.base_url}/query",
            json={
                "query": query,
                "session_id": session_id,
                "execution_pattern": pattern
            }
        )
        return response.json()
    
    def create_session(self, user_id: str = None):
        response = requests.post(
            f"{self.base_url}/sessions",
            json={"user_id": user_id}
        )
        return response.json()

# Usage
client = DocIntelClient()
session = client.create_session(user_id="user-123")
result = client.query(
    "What was Q3 2024 performance?",
    session_id=session["session_id"]
)
print(result["result"]["final_answer"])
\`\`\`

### JavaScript/TypeScript Client

\`\`\`typescript
class DocIntelClient {
  constructor(private baseUrl: string = "http://localhost:8000") {}

  async query(
    query: string,
    sessionId?: string,
    pattern: "sequential" | "parallel" | "loop" = "sequential"
  ) {
    const response = await fetch(\`\${this.baseUrl}/query\`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId, execution_pattern: pattern })
    });
    return response.json();
  }

  async createSession(userId?: string) {
    const response = await fetch(\`\${this.baseUrl}/sessions\`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId })
    });
    return response.json();
  }
}

// Usage
const client = new DocIntelClient();
const session = await client.createSession("user-123");
const result = await client.query(
  "What was Q3 2024 performance?",
  session.session_id
);
console.log(result.result.final_answer);
\`\`\`

---

## Next Steps

- [Architecture Guide](ARCHITECTURE.md) - Understand system design
- [Deployment Guide](DEPLOYMENT.md) - Set up and run the system
- [Evaluation Guide](EVALUATION.md) - See Kaggle alignment
