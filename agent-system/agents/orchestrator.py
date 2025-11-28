"""Orchestrator agent for coordinating multi-agent workflows."""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import google.generativeai as genai

from config import settings
from tools.rag_openapi_tool import RAGOpenAPITool


@dataclass
class AgentTask:
    """Represents a task for a specialist agent."""
    task_id: str
    agent_type: str  # "research", "analysis", "citation"
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowExecution:
    """Tracks the execution of a multi-agent workflow."""
    workflow_id: str
    user_query: str
    tasks: List[AgentTask] = field(default_factory=list)
    execution_pattern: str = "sequential"  # sequential, parallel, loop
    current_iteration: int = 0
    max_iterations: int = 3
    quality_threshold: float = 0.85
    final_result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class OrchestratorAgent:
    """
    Orchestrator agent that coordinates specialist agents.

    Demonstrates multi-agent patterns:
    - Sequential execution: Research → Analysis → Citation
    - Parallel execution: Multiple research queries simultaneously
    - Loop execution: Iterative quality improvement
    """

    def __init__(self):
        """Initialize orchestrator with Gemini model."""
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.rag_tool = RAGOpenAPITool()

        # Will be initialized with specialist agents
        self.research_agent = None
        self.analysis_agent = None
        self.citation_agent = None

    def register_agents(self, research_agent, analysis_agent, citation_agent):
        """Register specialist agents."""
        self.research_agent = research_agent
        self.analysis_agent = analysis_agent
        self.citation_agent = citation_agent

    async def execute_workflow(
        self,
        user_query: str,
        execution_pattern: str = "sequential",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute multi-agent workflow based on pattern.

        Args:
            user_query: User's question or request
            execution_pattern: "sequential", "parallel", or "loop"
            session_id: Optional session ID for memory persistence

        Returns:
            Dict with final result and execution metadata
        """
        workflow = WorkflowExecution(
            workflow_id=f"wf_{datetime.now().timestamp()}",
            user_query=user_query,
            execution_pattern=execution_pattern
        )

        # Step 1: Decompose user query into sub-tasks
        decomposition = await self._decompose_query(user_query)

        # Step 2: Execute based on pattern
        if execution_pattern == "sequential":
            result = await self._execute_sequential(workflow, decomposition)
        elif execution_pattern == "parallel":
            result = await self._execute_parallel(workflow, decomposition)
        elif execution_pattern == "loop":
            result = await self._execute_loop(workflow, decomposition)
        else:
            raise ValueError(f"Unknown execution pattern: {execution_pattern}")

        workflow.final_result = result
        workflow.completed_at = datetime.now()

        return {
            "workflow_id": workflow.workflow_id,
            "result": result,
            "execution_pattern": execution_pattern,
            "total_tasks": len(workflow.tasks),
            "duration_seconds": (workflow.completed_at - workflow.created_at).total_seconds(),
            "metadata": {
                "iterations": workflow.current_iteration if execution_pattern == "loop" else 1,
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "agent_type": task.agent_type,
                        "status": task.status
                    }
                    for task in workflow.tasks
                ]
            }
        }

    async def _decompose_query(self, user_query: str) -> Dict[str, Any]:
        """
        Use LLM to decompose complex query into sub-tasks.

        Returns:
            Dict with research queries, analysis requirements, citation needs
        """
        prompt = f"""You are a task decomposition expert. Given a user query about PE/VC documents,
break it down into specific sub-tasks for specialist agents.

User Query: {user_query}

Decompose into:
1. Research queries: What specific information needs to be retrieved?
2. Analysis tasks: What analysis needs to be performed on the data?
3. Citation requirements: What claims need citation validation?

Respond in JSON format:
{{
  "research_queries": ["query1", "query2", ...],
  "analysis_tasks": ["task1", "task2", ...],
  "citation_requirements": ["requirement1", ...],
  "complexity": "simple|moderate|complex"
}}
"""

        response = await self.model.generate_content_async(prompt)

        # Parse JSON from response
        import json
        try:
            # Extract JSON from markdown code blocks if present
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            decomposition = json.loads(text.strip())
            return decomposition
        except Exception as e:
            # Fallback to simple decomposition
            return {
                "research_queries": [user_query],
                "analysis_tasks": ["Analyze retrieved information"],
                "citation_requirements": ["Validate all claims"],
                "complexity": "simple"
            }

    async def _execute_sequential(
        self,
        workflow: WorkflowExecution,
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agents sequentially: Research → Analysis → Citation.

        This pattern ensures each stage completes before the next begins,
        allowing downstream agents to use upstream results.
        """
        results = {
            "pattern": "sequential",
            "stages": []
        }

        # Stage 1: Research
        research_results = []
        for idx, query in enumerate(decomposition["research_queries"]):
            task = AgentTask(
                task_id=f"research_{idx}",
                agent_type="research",
                query=query
            )
            workflow.tasks.append(task)

            task.status = "in_progress"
            result = await self.research_agent.execute(query)
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()

            research_results.append(result)

        results["stages"].append({
            "stage": "research",
            "results": research_results
        })

        # Stage 2: Analysis (uses research results)
        analysis_results = []
        for idx, analysis_task in enumerate(decomposition["analysis_tasks"]):
            task = AgentTask(
                task_id=f"analysis_{idx}",
                agent_type="analysis",
                query=analysis_task,
                context={"research_results": research_results}
            )
            workflow.tasks.append(task)

            task.status = "in_progress"
            result = await self.analysis_agent.execute(
                analysis_task,
                context=research_results
            )
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()

            analysis_results.append(result)

        results["stages"].append({
            "stage": "analysis",
            "results": analysis_results
        })

        # Stage 3: Citation validation (uses analysis results)
        citation_task = AgentTask(
            task_id="citation_validation",
            agent_type="citation",
            query="Validate all citations",
            context={"analysis_results": analysis_results}
        )
        workflow.tasks.append(citation_task)

        citation_task.status = "in_progress"
        citation_result = await self.citation_agent.execute(
            analysis_results,
            research_results
        )
        citation_task.result = citation_result
        citation_task.status = "completed"
        citation_task.completed_at = datetime.now()

        results["stages"].append({
            "stage": "citation",
            "results": citation_result
        })

        # Synthesize final answer
        final_answer = await self._synthesize_answer(
            workflow.user_query,
            research_results,
            analysis_results,
            citation_result
        )

        results["final_answer"] = final_answer
        return results

    async def _execute_parallel(
        self,
        workflow: WorkflowExecution,
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute multiple research queries in parallel for speed.

        This pattern is optimal when sub-tasks are independent and
        can be executed concurrently.
        """
        results = {
            "pattern": "parallel",
            "stages": []
        }

        # Execute all research queries in parallel
        tasks = []
        agent_tasks = []

        for idx, query in enumerate(decomposition["research_queries"]):
            task = AgentTask(
                task_id=f"research_{idx}",
                agent_type="research",
                query=query
            )
            workflow.tasks.append(task)
            agent_tasks.append(task)

            task.status = "in_progress"
            tasks.append(self.research_agent.execute(query))

        # Wait for all to complete
        research_results = await asyncio.gather(*tasks)

        # Update task statuses
        for task, result in zip(agent_tasks, research_results):
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()

        results["stages"].append({
            "stage": "parallel_research",
            "results": research_results
        })

        # Then proceed with sequential analysis and citation
        # (Analysis often depends on having all research complete)
        analysis_results = []
        for idx, analysis_task in enumerate(decomposition["analysis_tasks"]):
            task = AgentTask(
                task_id=f"analysis_{idx}",
                agent_type="analysis",
                query=analysis_task,
                context={"research_results": research_results}
            )
            workflow.tasks.append(task)

            task.status = "in_progress"
            result = await self.analysis_agent.execute(
                analysis_task,
                context=research_results
            )
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()

            analysis_results.append(result)

        results["stages"].append({
            "stage": "analysis",
            "results": analysis_results
        })

        # Citation validation
        citation_task = AgentTask(
            task_id="citation_validation",
            agent_type="citation",
            query="Validate all citations",
            context={"analysis_results": analysis_results}
        )
        workflow.tasks.append(citation_task)

        citation_task.status = "in_progress"
        citation_result = await self.citation_agent.execute(
            analysis_results,
            research_results
        )
        citation_task.result = citation_result
        citation_task.status = "completed"
        citation_task.completed_at = datetime.now()

        results["stages"].append({
            "stage": "citation",
            "results": citation_result
        })

        # Synthesize final answer
        final_answer = await self._synthesize_answer(
            workflow.user_query,
            research_results,
            analysis_results,
            citation_result
        )

        results["final_answer"] = final_answer
        return results

    async def _execute_loop(
        self,
        workflow: WorkflowExecution,
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute with iterative quality improvement loop.

        This pattern:
        1. Executes research → analysis → citation
        2. Evaluates quality
        3. If below threshold, refines and retries
        4. Stops at max iterations or quality threshold met
        """
        results = {
            "pattern": "loop",
            "iterations": []
        }

        for iteration in range(workflow.max_iterations):
            workflow.current_iteration = iteration + 1

            iteration_result = {
                "iteration": iteration + 1,
                "stages": []
            }

            # Research stage
            research_results = []
            for idx, query in enumerate(decomposition["research_queries"]):
                task = AgentTask(
                    task_id=f"research_{iteration}_{idx}",
                    agent_type="research",
                    query=query
                )
                workflow.tasks.append(task)

                task.status = "in_progress"
                result = await self.research_agent.execute(query)
                task.result = result
                task.status = "completed"
                task.completed_at = datetime.now()

                research_results.append(result)

            iteration_result["stages"].append({
                "stage": "research",
                "results": research_results
            })

            # Analysis stage
            analysis_results = []
            for idx, analysis_task in enumerate(decomposition["analysis_tasks"]):
                task = AgentTask(
                    task_id=f"analysis_{iteration}_{idx}",
                    agent_type="analysis",
                    query=analysis_task,
                    context={"research_results": research_results}
                )
                workflow.tasks.append(task)

                task.status = "in_progress"
                result = await self.analysis_agent.execute(
                    analysis_task,
                    context=research_results
                )
                task.result = result
                task.status = "completed"
                task.completed_at = datetime.now()

                analysis_results.append(result)

            iteration_result["stages"].append({
                "stage": "analysis",
                "results": analysis_results
            })

            # Citation validation
            citation_task = AgentTask(
                task_id=f"citation_{iteration}",
                agent_type="citation",
                query="Validate all citations",
                context={"analysis_results": analysis_results}
            )
            workflow.tasks.append(citation_task)

            citation_task.status = "in_progress"
            citation_result = await self.citation_agent.execute(
                analysis_results,
                research_results
            )
            citation_task.result = citation_result
            citation_task.status = "completed"
            citation_task.completed_at = datetime.now()

            iteration_result["stages"].append({
                "stage": "citation",
                "results": citation_result
            })

            # Evaluate quality
            quality_score = await self._evaluate_quality(
                research_results,
                analysis_results,
                citation_result
            )

            iteration_result["quality_score"] = quality_score
            results["iterations"].append(iteration_result)

            # Check if quality threshold met
            if quality_score >= workflow.quality_threshold:
                results["converged"] = True
                results["convergence_iteration"] = iteration + 1
                break

            # If not final iteration, refine queries for next round
            if iteration < workflow.max_iterations - 1:
                decomposition = await self._refine_decomposition(
                    decomposition,
                    research_results,
                    quality_score
                )

        # Synthesize final answer from best iteration
        best_iteration = max(
            results["iterations"],
            key=lambda x: x["quality_score"]
        )

        final_answer = await self._synthesize_answer(
            workflow.user_query,
            best_iteration["stages"][0]["results"],  # research
            best_iteration["stages"][1]["results"],  # analysis
            best_iteration["stages"][2]["results"]   # citation
        )

        results["final_answer"] = final_answer
        results["best_quality_score"] = best_iteration["quality_score"]

        return results

    async def _evaluate_quality(
        self,
        research_results: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]],
        citation_result: Dict[str, Any]
    ) -> float:
        """
        Evaluate quality of current iteration.

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Simple quality heuristic based on:
        # - Number of sources retrieved
        # - Citation accuracy
        # - Analysis completeness

        total_sources = sum(
            len(r.get("sources", []))
            for r in research_results
        )

        citation_accuracy = citation_result.get("accuracy", 0.0)

        analysis_completeness = sum(
            1 for a in analysis_results
            if a.get("status") == "completed"
        ) / max(len(analysis_results), 1)

        # Weighted average
        quality_score = (
            (min(total_sources / 10, 1.0) * 0.3) +  # 30% weight on sources
            (citation_accuracy * 0.5) +              # 50% weight on citations
            (analysis_completeness * 0.2)            # 20% weight on completeness
        )

        return quality_score

    async def _refine_decomposition(
        self,
        decomposition: Dict[str, Any],
        research_results: List[Dict[str, Any]],
        quality_score: float
    ) -> Dict[str, Any]:
        """Refine query decomposition based on previous iteration results."""
        # Use LLM to suggest refined queries
        prompt = f"""Previous iteration achieved quality score of {quality_score:.2f}.

Research queries: {decomposition['research_queries']}
Results summary: {len(research_results)} results retrieved

Suggest refined research queries to improve quality. Focus on gaps or missing information.

Respond in JSON format:
{{
  "research_queries": ["refined_query1", ...],
  "analysis_tasks": ["task1", ...],
  "citation_requirements": ["requirement1", ...],
  "refinement_rationale": "explanation"
}}
"""

        response = await self.model.generate_content_async(prompt)

        import json
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            refined = json.loads(text.strip())
            return refined
        except Exception:
            # If parsing fails, keep original
            return decomposition

    async def _synthesize_answer(
        self,
        user_query: str,
        research_results: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]],
        citation_result: Dict[str, Any]
    ) -> str:
        """Synthesize final answer from all agent results."""
        prompt = f"""You are synthesizing a comprehensive answer to a user query about PE/VC documents.

User Query: {user_query}

Research Results:
{self._format_research_results(research_results)}

Analysis Results:
{self._format_analysis_results(analysis_results)}

Citation Validation:
{citation_result}

Provide a comprehensive, well-cited answer that:
1. Directly addresses the user's query
2. Incorporates key findings from research
3. Includes relevant analysis insights
4. Properly cites all sources
5. Highlights any limitations or caveats

Answer:
"""

        response = await self.model.generate_content_async(prompt)
        return response.text

    def _format_research_results(self, results: List[Dict[str, Any]]) -> str:
        """Format research results for synthesis prompt."""
        formatted = []
        for idx, result in enumerate(results):
            sources = result.get("sources", [])
            answer = result.get("answer", "")

            formatted.append(f"Research Query {idx + 1}:")
            formatted.append(f"  Sources: {len(sources)} documents")
            formatted.append(f"  Answer: {answer[:200]}...")

        return "\n".join(formatted)

    def _format_analysis_results(self, results: List[Dict[str, Any]]) -> str:
        """Format analysis results for synthesis prompt."""
        formatted = []
        for idx, result in enumerate(results):
            formatted.append(f"Analysis {idx + 1}:")
            formatted.append(f"  {result}")

        return "\n".join(formatted)

    async def close(self):
        """Cleanup resources."""
        await self.rag_tool.close()
