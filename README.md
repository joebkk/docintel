# DocIntel

Multi-agent document intelligence system for PE/VC document analysis.

Kaggle AI Agents Competition submission demonstrating tool use, planning, multi-agent collaboration, parallelization, reflection, long-term memory, and human-in-the-loop workflows.

## Overview

DocIntel is a production-ready hybrid architecture combining:
- **TypeScript RAG Backend** - High-performance document search and retrieval
- **Python Multi-Agent System** - Intelligent orchestration and analysis
- **Observability Stack** - Comprehensive monitoring and tracing

## Key Features

### Kaggle AI Agents Concepts

1. **Tool Use** - Agents leverage RAG API, MongoDB, embeddings, and LLM tools
2. **Planning** - Orchestrator decomposes complex queries into sub-tasks
3. **Multi-Agent Collaboration** - 4 specialist agents working together
4. **Parallelization** - Concurrent task execution for performance
5. **Reflection** - Quality evaluation and iterative refinement
6. **Long-Term Memory** - Persistent memory bank with MongoDB
7. **Human-in-the-Loop** - Session management and checkpointing

### Technical Capabilities

- **Hybrid Search**: Lexical (BM25), Semantic (Vector), and Hybrid (RRF) search modes
- **Advanced PDF Processing**: LlamaParse integration for accurate text extraction
- **Scalable Architecture**: Docker Compose with 5 services
- **Production Monitoring**: Prometheus metrics, Grafana dashboards, Jaeger tracing
- **Enterprise LLMs**: AWS Bedrock Claude Sonnet 4.5, Google Gemini 2.0 Flash

## Quick Start

### Prerequisites

- Docker Desktop
- MongoDB Atlas account (free tier works)
- API Keys:
  - OpenAI API key
  - Google Gemini API key
  - AWS credentials (for Bedrock)
  - LlamaCloud API key

### Setup

1. **Clone and configure**:
\`\`\`bash
cd docintel

# Configure environment variables
cp rag-backend/.env.example rag-backend/.env
cp agent-system/.env.example agent-system/.env

# Edit .env files with your API keys
\`\`\`

2. **Create MongoDB Atlas indexes**:
   - Create \`doc_pages_search\` (Atlas Search index)
   - Create \`doc_chunks_vector\` (Vector Search index, 3072 dimensions)

   See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

3. **Start services**:
\`\`\`bash
docker compose up -d
\`\`\`

4. **Seed test documents**:
\`\`\`bash
docker exec docintel-rag node /app/scripts/seed-test-documents.js
\`\`\`

5. **Test the system**:
\`\`\`bash
# Test RAG backend
curl -X POST http://localhost:3000/api/unified-search \\
  -H "Content-Type: application/json" \\
  -d '{"query": "portfolio performance Q3 2024", "mode": "hybrid"}'

# Test agent system
curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{"query": "What were the Q3 2024 results?", "session_id": "test-123"}'
\`\`\`

## Services

| Service | Port | Description |
|---------|------|-------------|
| RAG Backend | 3000 | Document search and retrieval API |
| Agent System | 8000 | Multi-agent orchestration |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Monitoring dashboards |
| Jaeger | 16686 | Distributed tracing |

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System design and components
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOYMENT.md) - Setup and production deployment
- [Evaluation Guide](docs/EVALUATION.md) - Kaggle competition criteria mapping

## Technology Stack

### RAG Backend (TypeScript)
- **Framework**: Next.js 15, TypeScript
- **Search**: MongoDB Atlas Search (BM25), Atlas Vector Search (3072-dim)
- **LLM**: AWS Bedrock Claude Sonnet 4.5
- **Embeddings**: OpenAI text-embedding-3-large
- **Workflow**: Temporal (document processing)
- **PDF Parsing**: LlamaParse

### Agent System (Python)
- **Framework**: FastAPI, Python 3.11+
- **Agents**: Google Gemini 2.0 Flash
- **Orchestration**: Custom multi-agent framework
- **Memory**: MongoDB (persistent), In-memory (session)
- **Tools**: RAG API client, OpenAI embeddings

## Kaggle Competition Alignment

This system demonstrates all 7 required AI agent concepts:

1. **Tool Use** ✅ - 5+ tools (RAG API, MongoDB, embeddings, LLMs, search indexes)
2. **Planning** ✅ - Query decomposition and task routing
3. **Multi-Agent** ✅ - 4 specialist agents with distinct roles
4. **Parallelization** ✅ - Concurrent task execution
5. **Reflection** ✅ - Quality evaluation and iteration
6. **Memory** ✅ - Persistent MongoDB + session storage
7. **Human-in-Loop** ✅ - Checkpointing and session management

See [docs/EVALUATION.md](docs/EVALUATION.md) for detailed mapping.

## License

MIT License

---

**Built for Kaggle AI Agents Competition** | **Target Score: 98-100 points**
