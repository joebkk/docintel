"""FastAPI main application for DocIntel agent system."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
from contextlib import asynccontextmanager

from config import settings
from agents import OrchestratorAgent, ResearchAgent, AnalysisAgent, CitationAgent
from memory import InMemorySessionService, MemoryBank
from observability import (
    setup_logging,
    get_logger,
    setup_tracing,
    get_metrics,
    update_active_sessions
)


# Initialize logging and tracing
setup_logging()
logger = get_logger(__name__)
setup_tracing("docintel-agents")

# Global instances
session_service: Optional[InMemorySessionService] = None
memory_bank: Optional[MemoryBank] = None
orchestrator: Optional[OrchestratorAgent] = None
research_agent: Optional[ResearchAgent] = None
analysis_agent: Optional[AnalysisAgent] = None
citation_agent: Optional[CitationAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for startup and shutdown.
    """
    global session_service, memory_bank, orchestrator
    global research_agent, analysis_agent, citation_agent

    # Startup
    logger.info("starting_agent_system", service="docintel-agents")

    try:
        # Initialize memory systems
        session_service = InMemorySessionService()
        memory_bank = MemoryBank()

        # Initialize agents
        orchestrator = OrchestratorAgent()
        research_agent = ResearchAgent()
        analysis_agent = AnalysisAgent()
        citation_agent = CitationAgent()

        # Register specialist agents with orchestrator
        orchestrator.register_agents(
            research_agent,
            analysis_agent,
            citation_agent
        )

        logger.info("agent_system_started", status="success")

    except Exception as e:
        logger.error("agent_system_startup_failed", error=str(e), exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("shutting_down_agent_system")

    try:
        if orchestrator:
            await orchestrator.close()
        if research_agent:
            await research_agent.close()

        if memory_bank:
            memory_bank.close()

        logger.info("agent_system_shutdown_complete")

    except Exception as e:
        logger.error("shutdown_error", error=str(e))


# Create FastAPI app
app = FastAPI(
    title="DocIntel Agent System",
    description="Multi-agent system for PE/VC document intelligence",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models

class QueryRequest(BaseModel):
    """Request model for agent queries."""
    query: str = Field(..., description="User query")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    execution_pattern: str = Field("sequential", description="Execution pattern: sequential, parallel, or loop")
    user_id: Optional[str] = Field(None, description="User identifier")


class QueryResponse(BaseModel):
    """Response model for agent queries."""
    workflow_id: str
    result: Dict[str, Any]
    execution_pattern: str
    total_tasks: int
    duration_seconds: float
    session_id: Optional[str] = None


class ResearchRequest(BaseModel):
    """Request for direct research agent query."""
    query: str
    mode: str = "hybrid"
    file_names: Optional[List[str]] = None


class SessionResponse(BaseModel):
    """Response model for session info."""
    session_id: str
    user_id: Optional[str]
    message_count: int
    created_at: str
    updated_at: str


class MemoryRequest(BaseModel):
    """Request to store memory."""
    content: str
    memory_type: str = "fact"
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    importance: float = Field(0.5, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None


# Health check endpoint

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "docintel-agents",
        "version": "1.0.0"
    }


# Metrics endpoint for Prometheus

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    metrics_output, content_type = get_metrics()
    return Response(content=metrics_output, media_type=content_type)


# Agent query endpoints

@app.post("/query", response_model=QueryResponse)
async def query_agents(request: QueryRequest):
    """
    Execute multi-agent workflow for user query.

    This is the main entry point for agent interactions.
    """
    logger.info(
        "query_received",
        query=request.query[:100],
        execution_pattern=request.execution_pattern,
        session_id=request.session_id
    )

    try:
        # Get or create session
        if request.session_id:
            session = session_service.get_session(request.session_id)
            if not session:
                session = session_service.create_session(
                    session_id=request.session_id,
                    user_id=request.user_id
                )
        else:
            session = session_service.create_session(user_id=request.user_id)

        # Add user message to session
        session.add_message("user", request.query)

        # Execute workflow
        result = await orchestrator.execute_workflow(
            user_query=request.query,
            execution_pattern=request.execution_pattern,
            session_id=session.session_id
        )

        # Add assistant response to session
        final_answer = result["result"].get("final_answer", "")
        session.add_message("assistant", final_answer)

        # Save session
        session_service.save_session(session)

        # Update metrics
        update_active_sessions(len(session_service.sessions))

        logger.info(
            "query_completed",
            workflow_id=result["workflow_id"],
            duration=result["duration_seconds"]
        )

        return QueryResponse(
            workflow_id=result["workflow_id"],
            result=result["result"],
            execution_pattern=result["execution_pattern"],
            total_tasks=result["total_tasks"],
            duration_seconds=result["duration_seconds"],
            session_id=session.session_id
        )

    except Exception as e:
        logger.error("query_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research")
async def research_query(request: ResearchRequest):
    """
    Direct research agent query.

    Bypasses orchestrator for simple research-only queries.
    """
    try:
        result = await research_agent.execute(
            query=request.query,
            mode=request.mode,
            file_names=request.file_names
        )

        return result

    except Exception as e:
        logger.error("research_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Session management endpoints

@app.post("/sessions", response_model=SessionResponse)
async def create_session(user_id: Optional[str] = None):
    """Create a new session."""
    try:
        session = session_service.create_session(user_id=user_id)

        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            message_count=len(session.messages),
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat()
        )

    except Exception as e:
        logger.error("session_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session information."""
    session = session_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        message_count=len(session.messages),
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: Optional[int] = None):
    """Get session conversation history."""
    session = session_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.get_messages(limit=limit)

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat()
            }
            for m in messages
        ]
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    try:
        session_service.delete_session(session_id)
        update_active_sessions(len(session_service.sessions))

        return {"status": "deleted", "session_id": session_id}

    except Exception as e:
        logger.error("session_deletion_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Memory Bank endpoints

@app.post("/memory")
async def store_memory(request: MemoryRequest):
    """Store a memory in the Memory Bank."""
    try:
        memory = memory_bank.store_memory(
            content=request.content,
            memory_type=request.memory_type,
            session_id=request.session_id,
            user_id=request.user_id,
            importance=request.importance,
            tags=request.tags
        )

        return {
            "status": "stored",
            "entry_id": memory.entry_id,
            "memory_type": memory.memory_type
        }

    except Exception as e:
        logger.error("memory_storage_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory")
async def retrieve_memories(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    memory_type: Optional[str] = None,
    min_importance: Optional[float] = None,
    limit: int = 10
):
    """Retrieve memories from Memory Bank."""
    try:
        memories = memory_bank.retrieve_memories(
            user_id=user_id,
            session_id=session_id,
            memory_type=memory_type,
            min_importance=min_importance,
            limit=limit
        )

        return {
            "count": len(memories),
            "memories": [
                {
                    "entry_id": m.entry_id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat(),
                    "tags": m.tags
                }
                for m in memories
            ]
        }

    except Exception as e:
        logger.error("memory_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats")
async def get_memory_stats(user_id: Optional[str] = None):
    """Get Memory Bank statistics."""
    try:
        stats = memory_bank.get_memory_stats(user_id=user_id)
        return stats

    except Exception as e:
        logger.error("memory_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Checkpoint/Resume endpoints for long-running operations

@app.post("/sessions/{session_id}/checkpoint")
async def create_checkpoint(session_id: str):
    """Create a checkpoint of current session state."""
    try:
        checkpoint_id = session_service.create_checkpoint(session_id)

        return {
            "status": "checkpoint_created",
            "checkpoint_id": checkpoint_id,
            "session_id": session_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("checkpoint_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/checkpoints/{checkpoint_id}/restore")
async def restore_checkpoint(checkpoint_id: str):
    """Restore session from checkpoint."""
    try:
        session = session_service.restore_checkpoint(checkpoint_id)

        return {
            "status": "checkpoint_restored",
            "checkpoint_id": checkpoint_id,
            "session_id": session.session_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("checkpoint_restore_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.log_level.upper() == "DEBUG"
    )
