# Architecture Guide

## System Overview

DocIntel is a hybrid multi-agent system combining TypeScript and Python components for intelligent document analysis. The architecture is designed for production use with enterprise-grade observability, scalability, and reliability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (REST API clients, Jupyter notebooks, Web UI)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestration Layer                     │
│                   (Python FastAPI - Port 8000)                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Orchestrator Agent (Gemini)               │    │
│  │  • Query decomposition                                 │    │
│  │  • Task routing                                        │    │
│  │  • Result synthesis                                    │    │
│  │  • Quality reflection                                  │    │
│  └────────────────────────────────────────────────────────┘    │
│           ↓                ↓                ↓                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Research    │  │  Analysis    │  │  Citation    │         │
│  │   Agent      │  │   Agent      │  │   Agent      │         │
│  │  (Gemini)    │  │  (Gemini)    │  │  (Gemini)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│           ↓                ↓                ↓                   │
│  ┌─────────────────────────────────────────────────────┐       │
│  │            Memory & Session Management              │       │
│  │  • MongoDB Memory Bank (persistent)                 │       │
│  │  • In-Memory Session Store (transient)              │       │
│  │  • Checkpointing (resume capability)                │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RAG Backend Layer                           │
│                   (TypeScript Next.js - Port 3000)              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Search Services                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │   Lexical    │  │   Semantic   │  │   Hybrid     │  │   │
│  │  │  (BM25)      │  │   (Vector)   │  │   (RRF)      │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Answer Generation                          │   │
│  │  • AWS Bedrock Claude Sonnet 4.5                       │   │
│  │  • Streaming responses                                 │   │
│  │  • Citation formatting                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Document Processing Pipeline                  │   │
│  │  • Temporal workflows                                   │   │
│  │  • LlamaParse (PDF → Markdown)                         │   │
│  │  • OpenAI embeddings (3072-dim)                        │   │
│  │  • Chunking & storage                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Data & Storage Layer                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │               MongoDB Atlas                           │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │      │
│  │  │  doc_pages   │  │  doc_chunks  │  │agent_memory│ │      │
│  │  │ (full text)  │  │ (embeddings) │  │  (facts)   │ │      │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │      │
│  │                                                       │      │
│  │  Indexes:                                            │      │
│  │  • doc_pages_search (Atlas Search - BM25)           │      │
│  │  • doc_chunks_vector (Vector Search - 3072-dim)     │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │      DigitalOcean Spaces (Optional)                  │      │
│  │  • PDF file storage                                  │      │
│  │  • Presigned URLs for access                        │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Observability Layer                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Prometheus  │  │   Grafana    │  │    Jaeger    │         │
│  │  (Metrics)   │  │ (Dashboards) │  │  (Tracing)   │         │
│  │   :9090      │  │    :3001     │  │   :16686     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Agent Orchestration Layer

#### Orchestrator Agent
**Role**: Central coordinator and planner

**Responsibilities**:
- **Query Decomposition**: Breaks complex user queries into sub-tasks
- **Task Routing**: Determines which specialist agents to engage
- **Execution Patterns**: Supports sequential, parallel, and loop execution
- **Result Synthesis**: Combines specialist agent outputs into coherent response
- **Quality Reflection**: Evaluates output quality and triggers iterations

**Implementation**: `agent-system/agents/orchestrator.py`

**Key Methods**:
- `execute_workflow()` - Main entry point
- `_decompose_query()` - LLM-powered task breakdown
- `_execute_sequential()` - Linear execution
- `_execute_parallel()` - Concurrent execution with asyncio
- `_execute_loop()` - Iterative refinement with quality checks

#### Research Agent
**Role**: Information retrieval specialist

**Responsibilities**:
- Query RAG backend for document search
- Enhance RAG responses with structured summaries
- Extract key facts from sources
- Identify information gaps

**Tools Used**:
- RAG API (lexical, semantic, hybrid search)
- Gemini 2.0 Flash (summary enhancement)

**Implementation**: `agent-system/agents/research_agent.py`

#### Analysis Agent
**Role**: Quantitative and qualitative analysis

**Responsibilities**:
- Extract and analyze numerical metrics
- Perform comparative analysis across documents
- Generate trend insights
- Calculate aggregations and statistics

**Implementation**: `agent-system/agents/analysis_agent.py`

#### Citation Agent
**Role**: Fact verification and citation

**Responsibilities**:
- Validate claims against source documents
- Generate proper citations with page numbers
- Assign confidence scores to statements
- Flag unsupported claims

**Implementation**: `agent-system/agents/citation_agent.py`

### 2. RAG Backend Layer

#### Search Service Architecture

**Lexical Search** (`search-service.ts:lexicalSearch`)
- Algorithm: BM25 (Best Match 25)
- Index: MongoDB Atlas Search (`doc_pages_search`)
- Collection: `doc_pages` (full document pages)
- Use case: Exact keyword matching, terminology search

**Semantic Search** (`search-service.ts:semanticSearch`)
- Algorithm: Cosine similarity on 3072-dim vectors
- Index: MongoDB Atlas Vector Search (`doc_chunks_vector`)
- Embeddings: OpenAI `text-embedding-3-large`
- Collection: `doc_chunks` (chunked documents with embeddings)
- Use case: Conceptual similarity, paraphrase matching

**Hybrid Search** (`search-service.ts:hybridSearch`)
- Algorithm: Reciprocal Rank Fusion (RRF)
- Formula: `RRF_score = Σ(1 / (k + rank_i))` where k=60
- Combines: Lexical + Semantic results
- Use case: Best of both worlds

#### Document Processing Pipeline

**Workflow Steps** (`temporal/workflows/document-processing.ts`):
1. **Check State**: Deduplication via ETag comparison
2. **Fetch Blob**: Download PDF from DigitalOcean Spaces
3. **Parse**: LlamaParse extracts text page-by-page
4. **Store Pages**: Save to `doc_pages` collection
5. **Generate Embeddings**: OpenAI creates 3072-dim vectors
6. **Chunk & Store**: Save to `doc_chunks` with embeddings
7. **Update State**: Mark as completed in `document_state`
8. **Log History**: Record in `processing_history`

**Technologies**:
- **Temporal**: Durable workflow orchestration
- **LlamaParse**: PDF → Markdown conversion
- **OpenAI**: Embedding generation

### 3. Memory Systems

#### Memory Bank (Persistent)
**Storage**: MongoDB `agent_memory` collection

**Schema**:
\`\`\`python
{
  "entry_id": str,           # UUID
  "content": str,            # Fact or insight
  "memory_type": str,        # "fact", "preference", "insight"
  "session_id": str | None,  # Optional session link
  "user_id": str | None,     # Optional user link
  "importance": float,       # 0.0-1.0 relevance score
  "tags": List[str],         # Categorization
  "created_at": datetime,
  "access_count": int,       # Usage tracking
  "last_accessed": datetime
}
\`\`\`

**Features**:
- Importance-based retrieval
- Tag filtering
- Session/user scoping
- LRU-style access tracking

#### Session Storage (Transient)
**Storage**: In-memory Python dictionaries

**Schema**:
\`\`\`python
{
  "session_id": str,
  "user_id": str | None,
  "messages": List[Message],  # Conversation history
  "created_at": datetime,
  "updated_at": datetime
}
\`\`\`

**Features**:
- Checkpointing (save/restore state)
- Message history
- Automatic expiration

### 4. Observability

#### Metrics (Prometheus)
**Endpoint**: `http://localhost:9090`

**Key Metrics**:
- `agent_active_sessions` - Current session count
- `agent_workflow_duration_seconds` - Execution time histogram
- `agent_workflow_total` - Counter by pattern (sequential/parallel/loop)
- `agent_llm_tokens_total` - Token usage tracking
- `agent_llm_cost_usd` - Estimated costs

**Implementation**: `observability/metrics.py`

#### Dashboards (Grafana)
**Endpoint**: `http://localhost:3001`

**Pre-configured Dashboards**:
- Agent System Overview
- Workflow Performance
- LLM Usage & Costs
- Error Rates

#### Tracing (Jaeger)
**Endpoint**: `http://localhost:16686`

**Spans**:
- Workflow execution
- Agent calls
- RAG API requests
- Database queries

**Implementation**: OpenTelemetry SDK

## Data Flow Examples

### Example 1: Simple Query (Sequential)

\`\`\`
User: "What was our Q3 2024 IRR?"

1. Orchestrator receives query
   ↓
2. Decomposes into task:
   {
     "research_queries": ["Q3 2024 IRR performance"],
     "analysis_tasks": ["extract IRR metric"],
     "citation_requirements": ["verify source"]
   }
   ↓
3. Research Agent:
   • Queries RAG: "Q3 2024 IRR performance" (hybrid mode)
   • RAG searches MongoDB (lexical + semantic)
   • RAG generates answer with Bedrock Claude
   • Returns: "15% IRR" with sources
   ↓
4. Analysis Agent:
   • Extracts numeric value: 15%
   • Compares to historical data
   • Returns: "15% IRR, up from 12% in Q2"
   ↓
5. Citation Agent:
   • Verifies "15% IRR" appears in Q3_2024_Portfolio_Report.pdf
   • Returns: Citation with 95% confidence
   ↓
6. Orchestrator synthesizes:
   • Combines all agent outputs
   • Formats final response
   • Returns to user
\`\`\`

### Example 2: Complex Query (Parallel)

\`\`\`
User: "Compare Q3 2024 performance across all portfolio companies"

1. Orchestrator decomposes into multiple research tasks
   ↓
2. Executes in parallel:
   [Research Q3 metrics] + [Research company list] + [Research benchmarks]
   ↓
3. Analysis Agent processes results concurrently
   ↓
4. Citation Agent validates all claims in parallel
   ↓
5. Orchestrator synthesizes comparison table
\`\`\`

### Example 3: Iterative Query (Loop)

\`\`\`
User: "Summarize all due diligence reports"

Iteration 1:
  • Research: Find DD reports
  • Analysis: Extract key points
  • Quality check: Coverage = 60% → CONTINUE
  ↓
Iteration 2:
  • Research: Find additional DD details
  • Analysis: Enhance summary
  • Quality check: Coverage = 90% → COMPLETE
\`\`\`

## Scalability Considerations

### Horizontal Scaling

**RAG Backend**:
- Stateless Next.js API
- Can run multiple replicas behind load balancer
- MongoDB Atlas scales automatically

**Agent System**:
- FastAPI supports multiple workers
- Can deploy multiple instances
- Session affinity required for in-memory sessions

### Performance Optimization

**Caching**:
- LlamaParse results cached in MongoDB
- Embedding generation cached
- Session data cached in-memory

**Concurrency**:
- Asyncio for parallel agent execution
- Connection pooling for MongoDB
- HTTP/2 for API calls

**Resource Limits**:
- Docker memory limits configured
- LLM rate limiting implemented
- Concurrent request throttling

## Security

### API Authentication

**Webhook Security**:
- Bearer token authentication
- API key validation
- HTTPS enforcement (production)

**Inter-service Communication**:
- Docker network isolation
- Service-to-service authentication
- No exposed MongoDB ports

### Data Protection

**Sensitive Data**:
- API keys in environment variables
- MongoDB credentials encrypted
- No secrets in logs

**Access Control**:
- User-scoped sessions
- Memory isolation by user
- Document-level permissions (future)

## Deployment Architecture

### Docker Compose (Development/Testing)

\`\`\`yaml
services:
  rag-backend:        # Next.js API
  agent-system:       # FastAPI agents
  prometheus:         # Metrics
  grafana:           # Dashboards  
  jaeger:            # Tracing
\`\`\`

### Production (Kubernetes - Future)

\`\`\`
┌─────────────────────────────────────┐
│         Load Balancer               │
└─────────────────────────────────────┘
           ↓              ↓
    ┌──────────┐    ┌──────────┐
    │ RAG Pod  │    │Agent Pod │
    │ (3 replicas)   (2 replicas)
    └──────────┘    └──────────┘
           ↓              ↓
    ┌────────────────────────┐
    │   MongoDB Atlas        │
    │   (Managed Service)    │
    └────────────────────────┘
\`\`\`

## Technology Choices

### Why TypeScript for RAG Backend?
- Fast development with Next.js
- Strong typing for search logic
- Excellent MongoDB driver
- Easy Temporal integration

### Why Python for Agents?
- Best LLM library support (Google, OpenAI)
- Async/await for parallelization
- Rich data processing libraries
- FastAPI performance

### Why MongoDB Atlas?
- Native search capabilities (BM25)
- Native vector search (no separate DB)
- Managed service (no ops overhead)
- Excellent scaling

### Why Gemini for Agents?
- Fast inference (low latency)
- Cost-effective (free tier + cheap)
- Good at reasoning/planning
- Strong JSON output

### Why Bedrock Claude for RAG?
- Superior comprehension
- Better citation accuracy
- Streaming support
- Enterprise reliability

## Future Enhancements

1. **Streaming Agent Responses**: Real-time updates during long workflows
2. **Vector Similarity Search for Memory**: Find similar past queries
3. **User Authentication**: Multi-tenant support
4. **Advanced Reflection**: Self-correction with validation tools
5. **Graph-based Memory**: Knowledge graph for complex relationships
6. **Federated Search**: Query multiple data sources
7. **Auto-scaling**: Kubernetes HPA based on queue depth
8. **Advanced Observability**: Custom Grafana dashboards per user

---

**Next**: See [API_REFERENCE.md](API_REFERENCE.md) for detailed endpoint documentation.
