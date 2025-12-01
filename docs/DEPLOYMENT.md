# Deployment Guide

Complete guide for setting up and deploying DocIntel locally and in production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Docker Deployment](#docker-deployment)
- [MongoDB Atlas Setup](#mongodb-atlas-setup)
- [Environment Configuration](#environment-configuration)
- [Testing the System](#testing-the-system)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker Desktop** (v20.10+)
  - MacOS: [Download](https://www.docker.com/products/docker-desktop)
  - Windows: [Download](https://www.docker.com/products/docker-desktop)
  - Linux: `sudo apt-get install docker-ce docker-ce-cli`

- **Node.js** (v20+) - For local development
  - [Download](https://nodejs.org/)

- **Python** (v3.11+) - For local development
  - [Download](https://www.python.org/downloads/)

### Required Accounts & API Keys

1. **MongoDB Atlas** (Free tier works)
   - Sign up: https://www.mongodb.com/cloud/atlas/register
   - Create cluster (M0 Free tier recommended for testing)

2. **OpenAI API** (For embeddings)
   - Sign up: https://platform.openai.com/signup
   - Create API key: https://platform.openai.com/api-keys
   - **Cost**: ~$0.13 per 1M tokens (text-embedding-3-large)

3. **Google Gemini API** (For agents)
   - Sign up: https://ai.google.dev/
   - Create API key: https://aistudio.google.com/app/apikey
   - **Free tier**: 10 requests/minute

4. **AWS Bedrock** (For RAG answers)
   - Sign up: https://aws.amazon.com/bedrock/
   - Create access keys: AWS Console → IAM → Users
   - Enable Claude Sonnet 4.5 model access
   - **Cost**: $3 per 1M input tokens, $15 per 1M output tokens

5. **LlamaCloud** (For PDF parsing)
   - Sign up: https://cloud.llamaindex.ai/
   - Create API key from dashboard
   - **Free tier**: 1000 pages/month

---

## Local Development Setup

### 1. Clone Repository

\`\`\`bash
cd /path/to/workspace
git clone https://github.com/yourusername/docintel.git
cd docintel
\`\`\`

### 2. Install Dependencies

**RAG Backend (TypeScript)**:
\`\`\`bash
cd rag-backend
pnpm install  # or npm install
cd ..
\`\`\`

**Agent System (Python)**:
\`\`\`bash
cd agent-system
pip install -r requirements.txt
cd ..
\`\`\`

### 3. Run Services Locally (Without Docker)

**Terminal 1 - RAG Backend**:
\`\`\`bash
cd rag-backend
cp .env.example .env
# Edit .env with your API keys
pnpm dev
\`\`\`

**Terminal 2 - Agent System**:
\`\`\`bash
cd agent-system
cp .env.example .env
# Edit .env with your API keys
python main.py
\`\`\`

---

## Docker Deployment

### 1. Create Environment Files

**RAG Backend** (`.env`):
\`\`\`bash
cd rag-backend
cat > .env << EOF
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=docurepo_test
OPENAI_API_KEY=sk-...
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
LLAMA_CLOUD_API_KEY=llx-...
EOF
\`\`\`

**Agent System** (`.env`):
\`\`\`bash
cd agent-system
cat > .env << EOF
RAG_API_URL=http://rag-backend:3000
GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash-exp
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=docurepo_test
OPENAI_API_KEY=sk-...
EOF
\`\`\`

### 2. Build and Start Services

\`\`\`bash
# From project root
docker compose up -d
\`\`\`

**What this starts**:
- `docintel-rag` - RAG Backend (port 3000)
- `docintel-agents` - Agent System (port 8000)
- `prometheus` - Metrics (port 9090)
- `grafana` - Dashboards (port 3001)
- `jaeger` - Tracing (port 16686)

### 3. Verify Services

\`\`\`bash
# Check all containers are running
docker compose ps

# Should show all services as "healthy" or "running"
NAME                STATUS
docintel-rag        Up 30 seconds (healthy)
docintel-agents     Up 30 seconds (healthy)
prometheus          Up 30 seconds
grafana             Up 30 seconds
jaeger              Up 30 seconds
\`\`\`

### 4. View Logs

\`\`\`bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f agent-system
docker compose logs -f rag-backend
\`\`\`

---

## MongoDB Atlas Setup

### 1. Create Cluster

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Click "Build a Database"
3. Choose **M0 Free** tier
4. Select cloud provider and region
5. Name cluster (e.g., `docintel-cluster`)
6. Click "Create Cluster"

### 2. Configure Network Access

1. Navigate to **Network Access**
2. Click "Add IP Address"
3. For testing: Add `0.0.0.0/0` (allow all)
4. For production: Add your specific IP addresses
5. Click "Confirm"

### 3. Create Database User

1. Navigate to **Database Access**
2. Click "Add New Database User"
3. Choose **Password** authentication
4. Username: `docintel_user`
5. Password: Generate secure password
6. Database User Privileges: **Read and write to any database**
7. Click "Add User"

### 4. Get Connection String

1. Navigate to **Database** → **Connect**
2. Choose "Connect your application"
3. Driver: Node.js / Python
4. Copy connection string:
   \`\`\`
   mongodb+srv://docintel_user:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
   \`\`\`
5. Replace `<password>` with actual password
6. Add to `.env` files as `MONGODB_URI`

### 5. Create Database & Collections

\`\`\`bash
# Connect with mongosh
mongosh "mongodb+srv://docintel_user:<password>@cluster.mongodb.net/"

# Create database
use docurepo_test

# Collections will be created automatically on first insert
\`\`\`

### 6. Create Search Indexes

#### Lexical Search Index (BM25)

1. Navigate to **Database** → **Search**
2. Click "Create Search Index"
3. Configuration method: **JSON Editor**
4. Index name: `doc_pages_search`
5. Database: `docurepo_test`
6. Collection: `doc_pages`
7. Index definition:

\`\`\`json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "text": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "title": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "filename": {
        "type": "string"
      }
    }
  }
}
\`\`\`

8. Click "Create Search Index"

#### Vector Search Index

1. Navigate to **Database** → **Search**
2. Click "Create Search Index"
3. Configuration method: **JSON Editor**
4. Index name: `doc_chunks_vector`
5. Database: `docurepo_test`
6. Collection: `doc_chunks`
7. Index definition:

\`\`\`json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 3072,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "filename"
    },
    {
      "type": "filter",
      "path": "documentId"
    }
  ]
}
\`\`\`

8. Click "Create Search Index"

**Wait ~5 minutes for indexes to build.**

---

## Environment Configuration

### RAG Backend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.net/` |
| `MONGODB_DATABASE` | Database name | `docurepo_test` |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | `sk-...` |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `...` |
| `LLAMA_CLOUD_API_KEY` | LlamaCloud API key | `llx-...` |

### Agent System Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RAG_API_URL` | RAG backend URL | `http://rag-backend:3000` (Docker) or `http://localhost:3000` (local) |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.0-flash-exp` |
| `MONGODB_URI` | MongoDB connection string | Same as RAG backend |
| `MONGODB_DATABASE` | Database name | `docurepo_test` |
| `OPENAI_API_KEY` | OpenAI API key | Same as RAG backend |
| `LOG_LEVEL` | Logging level | `INFO` or `DEBUG` |

---

## Testing the System

### 1. Seed Test Documents

\`\`\`bash
docker exec docintel-rag node /app/scripts/seed-test-documents.js
\`\`\`

**Expected output**:
\`\`\`
🔌 Connecting to MongoDB...
✅ Connected to MongoDB Atlas
🗑️  Clearing existing test documents...
📝 Inserting sample documents...
✅ Inserted 3 documents
🎉 Seeding complete!
\`\`\`

### 2. Test RAG Backend

\`\`\`bash
curl -X POST http://localhost:3000/api/unified-search \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What was the Q3 2024 portfolio performance?",
    "mode": "hybrid"
  }'
\`\`\`

**Expected**: Streaming response with sources and answer

### 3. Test Agent System

**Wait 60 seconds if you hit Gemini quota, then:**

\`\`\`bash
curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What were the Q3 2024 results?",
    "session_id": "test-123"
  }'
\`\`\`

**Expected**: JSON with final_answer, sources, analysis, citations

### 4. Test Observability

**Prometheus**:
\`\`\`bash
# Open in browser
open http://localhost:9090
\`\`\`

**Grafana**:
\`\`\`bash
# Open in browser
open http://localhost:3001
# Default login: admin / admin
\`\`\`

**Jaeger**:
\`\`\`bash
# Open in browser
open http://localhost:16686
\`\`\`

---

## Production Deployment

### Kubernetes (Recommended)

**architecture.yaml**:
\`\`\`yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-backend
  template:
    metadata:
      labels:
        app: rag-backend
    spec:
      containers:
      - name: rag-backend
        image: docintel/rag-backend:latest
        ports:
        - containerPort: 3000
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: docintel-secrets
              key: mongodb-uri
---
apiVersion: v1
kind: Service
metadata:
  name: rag-backend
spec:
  selector:
    app: rag-backend
  ports:
  - port: 3000
    targetPort: 3000
  type: LoadBalancer
\`\`\`

**Deploy**:
\`\`\`bash
kubectl apply -f architecture.yaml
\`\`\`

### Cloud Providers

**AWS ECS**:
- Use Fargate for serverless containers
- RDS for MongoDB (or keep Atlas)
- CloudWatch for observability

**Google Cloud Run**:
- Deploy each service as Cloud Run service
- Cloud SQL or MongoDB Atlas
- Cloud Logging/Monitoring

**Azure Container Instances**:
- Deploy containers to ACI
- Cosmos DB or MongoDB Atlas
- Azure Monitor

---

## Troubleshooting

### Issue: Docker containers not starting

**Check**:
\`\`\`bash
docker compose logs
\`\`\`

**Common causes**:
- Port 3000 or 8000 already in use → Kill existing processes
- Missing .env files → Create .env in both directories
- Out of memory → Increase Docker memory limit

**Fix**:
\`\`\`bash
# Kill processes on port 3000
lsof -ti:3000 | xargs kill -9

# Restart Docker
docker compose down
docker compose up -d
\`\`\`

---

### Issue: MongoDB connection timeout

**Error**: `ServerSelectionTimeoutError: timed out`

**Causes**:
1. IP not whitelisted in MongoDB Atlas
2. Wrong connection string
3. Network firewall blocking connection

**Fix**:
1. Go to MongoDB Atlas → Network Access
2. Add current IP address or `0.0.0.0/0` (testing only)
3. Wait 1-2 minutes for changes to propagate
4. Retry connection

---

### Issue: Search returns no results

**Causes**:
1. Indexes not created
2. Indexes still building
3. Wrong collection/database name

**Fix**:
\`\`\`bash
# Verify documents exist
docker exec docintel-rag node -e "
const { MongoClient } = require('mongodb');
const client = new MongoClient(process.env.MONGODB_URI);
client.connect().then(async () => {
  const count = await client.db('docurepo_test').collection('doc_pages').countDocuments();
  console.log('Documents:', count);
  client.close();
});
"

# Check indexes in Atlas UI
# Database → Search → Verify both indexes exist and status = "Active"
\`\`\`

---

### Issue: Gemini quota exceeded

**Error**: `429 You exceeded your current quota`

**Solutions**:
1. **Wait**: 60 seconds between requests (free tier)
2. **Upgrade**: Get paid Gemini API tier
3. **Alternative**: Modify code to use different LLM

---

### Issue: Agent responses are slow

**Causes**:
1. Sequential execution for parallelizable tasks
2. Cold start (first request)
3. Large documents

**Optimizations**:
\`\`\`json
// Use parallel execution
{
  "query": "...",
  "execution_pattern": "parallel"  // Instead of "sequential"
}
\`\`\`

**Expected performance**:
- Sequential: 10-20s
- Parallel: 5-10s
- Loop: 15-30s (multiple iterations)

---

## Maintenance

### Update Dependencies

\`\`\`bash
# RAG backend
cd rag-backend && pnpm update

# Agent system
cd agent-system && pip install --upgrade -r requirements.txt
\`\`\`

### Backup MongoDB

\`\`\`bash
# Using mongodump
mongodump --uri="mongodb+srv://user:pass@cluster.net/docurepo_test" --out=backup/

# Restore
mongorestore --uri="mongodb+srv://user:pass@cluster.net/" backup/
\`\`\`

### Monitor Costs

**OpenAI**:
- Dashboard: https://platform.openai.com/usage
- Set spending limits in Settings

**AWS Bedrock**:
- CloudWatch → Bedrock metrics
- Set billing alerts

**Gemini**:
- Free tier: 10 req/min
- Paid: https://ai.google.dev/pricing

---

## Security Best Practices

1. **Never commit `.env` files**
   - Add to `.gitignore`
   - Use secrets management in production

2. **Rotate API keys regularly**
   - Every 90 days minimum

3. **Use MongoDB Atlas IP whitelist**
   - Don't use `0.0.0.0/0` in production
   - Add only necessary IPs

4. **Enable HTTPS in production**
   - Use SSL certificates
   - Terminate SSL at load balancer

5. **Implement authentication**
   - Add JWT tokens to agent APIs
   - Use API keys for webhook

---

## Next Steps

- [API Reference](API_REFERENCE.md) - Learn the APIs
- [Architecture Guide](ARCHITECTURE.md) - Understand the system
- [Evaluation Guide](EVALUATION.md) - See Kaggle alignment

---

**Need help?** Check logs or create an issue on GitHub.
