"""Agent evaluator for comprehensive quality assessment."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from .metrics import (
    EvaluationMetrics,
    calculate_retrieval_metrics,
    calculate_citation_accuracy,
    calculate_business_impact,
    calculate_overall_quality_score
)


@dataclass
class EvaluationResult:
    """Result of agent evaluation."""
    test_id: str
    query: str
    workflow_result: Dict[str, Any]
    metrics: EvaluationMetrics
    timestamp: datetime
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "test_id": self.test_id,
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics.to_dict(),
            "workflow_summary": {
                "execution_pattern": self.workflow_result.get("execution_pattern"),
                "total_tasks": self.workflow_result.get("total_tasks"),
                "duration_seconds": self.workflow_result.get("duration_seconds")
            },
            "notes": self.notes
        }


class AgentEvaluator:
    """
    Comprehensive evaluator for agent system performance.

    Provides:
    - Retrieval quality evaluation
    - Citation accuracy assessment
    - Business impact measurement
    - Comparative testing
    - Report generation
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize evaluator.

        Args:
            output_dir: Directory for evaluation reports
        """
        self.output_dir = Path(output_dir or "./evaluation_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[EvaluationResult] = []

    async def evaluate_workflow(
        self,
        test_id: str,
        query: str,
        workflow_result: Dict[str, Any],
        ground_truth: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> EvaluationResult:
        """
        Evaluate a complete workflow execution.

        Args:
            test_id: Unique test identifier
            query: Original query
            workflow_result: Result from orchestrator
            ground_truth: Optional ground truth for comparison
            notes: Optional notes about this test

        Returns:
            EvaluationResult with metrics
        """
        metrics = EvaluationMetrics()

        # Extract workflow components
        result_data = workflow_result.get("result", {})
        stages = result_data.get("stages", [])

        # Step 1: Evaluate retrieval quality
        if ground_truth and "relevant_documents" in ground_truth:
            retrieval_metrics = self._evaluate_retrieval(
                stages,
                ground_truth["relevant_documents"]
            )

            metrics.precision = retrieval_metrics["precision"]
            metrics.recall = retrieval_metrics["recall"]
            metrics.f1_score = retrieval_metrics["f1_score"]
            metrics.mrr = retrieval_metrics["mrr"]
            metrics.ndcg = retrieval_metrics["ndcg"]

        # Step 2: Evaluate citation accuracy
        citation_metrics = self._evaluate_citations(stages)

        metrics.citation_accuracy = citation_metrics.get("citation_accuracy", 0.0)
        metrics.supported_claims_ratio = citation_metrics.get("supported_claims_ratio", 0.0)
        metrics.citation_quality_score = citation_metrics.get("citation_quality_score", 0.0)

        # Step 3: Calculate business impact
        business_metrics = self._calculate_business_impact(
            workflow_result,
            stages,
            citation_metrics
        )

        metrics.time_savings_minutes = business_metrics["time_savings_minutes"]
        metrics.cost_savings_dollars = business_metrics["cost_savings_dollars"]
        metrics.accuracy_improvement = business_metrics["accuracy_improvement"]

        # Step 4: Calculate overall quality score
        metrics.overall_quality_score = calculate_overall_quality_score(metrics)

        # Create result
        evaluation_result = EvaluationResult(
            test_id=test_id,
            query=query,
            workflow_result=workflow_result,
            metrics=metrics,
            timestamp=datetime.now(),
            notes=notes
        )

        self.results.append(evaluation_result)

        return evaluation_result

    def _evaluate_retrieval(
        self,
        stages: List[Dict[str, Any]],
        ground_truth_docs: List[str]
    ) -> Dict[str, float]:
        """Evaluate retrieval quality against ground truth."""
        # Extract retrieved documents from research stage
        retrieved_docs = []

        for stage in stages:
            if stage.get("stage") == "research" or stage.get("stage") == "parallel_research":
                results = stage.get("results", [])

                for result in results:
                    if isinstance(result, dict) and "sources" in result:
                        for source in result["sources"]:
                            doc_id = source.get("fileName", source.get("documentKey", ""))
                            if doc_id:
                                retrieved_docs.append(doc_id)

        # Remove duplicates while preserving order
        retrieved_docs = list(dict.fromkeys(retrieved_docs))

        return calculate_retrieval_metrics(
            retrieved_docs,
            ground_truth_docs,
            k=10
        )

    def _evaluate_citations(self, stages: List[Dict[str, Any]]) -> Dict[str, float]:
        """Evaluate citation accuracy from citation stage."""
        # Find citation stage
        citation_result = None

        for stage in stages:
            if stage.get("stage") == "citation":
                citation_result = stage.get("results")
                break

        if not citation_result:
            return {
                "citation_accuracy": 0.0,
                "supported_claims_ratio": 0.0,
                "citation_quality_score": 0.0
            }

        # Extract validations
        validations = citation_result.get("validations", [])

        if not validations:
            return {
                "citation_accuracy": 0.0,
                "supported_claims_ratio": 0.0,
                "citation_quality_score": 0.0
            }

        # Calculate metrics
        return calculate_citation_accuracy([], validations)

    def _calculate_business_impact(
        self,
        workflow_result: Dict[str, Any],
        stages: List[Dict[str, Any]],
        citation_metrics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate business impact metrics."""
        # Count documents analyzed
        num_documents = 0
        for stage in stages:
            if stage.get("stage") in ["research", "parallel_research"]:
                for result in stage.get("results", []):
                    if isinstance(result, dict) and "sources" in result:
                        num_documents += len(result["sources"])

        # Count claims validated
        num_claims = citation_metrics.get("total_claims", 0)

        # Get execution duration
        duration_seconds = workflow_result.get("duration_seconds", 0.0)

        # Get citation accuracy
        citation_accuracy = citation_metrics.get("citation_accuracy", 0.0)

        return calculate_business_impact(
            duration_seconds,
            num_documents,
            num_claims,
            citation_accuracy
        )

    def generate_report(
        self,
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive evaluation report.

        Args:
            output_file: Optional file path for report

        Returns:
            Report content as string
        """
        if not self.results:
            return "No evaluation results available."

        # Calculate aggregate statistics
        avg_metrics = self._calculate_aggregate_metrics()

        report_lines = []

        report_lines.append("# Agent System Evaluation Report")
        report_lines.append(f"\n**Generated:** {datetime.now().isoformat()}")
        report_lines.append(f"**Total Tests:** {len(self.results)}\n")

        # Summary statistics
        report_lines.append("## Summary Statistics\n")
        report_lines.append("### Retrieval Quality")
        report_lines.append(f"- **Precision:** {avg_metrics['precision']:.3f}")
        report_lines.append(f"- **Recall:** {avg_metrics['recall']:.3f}")
        report_lines.append(f"- **F1 Score:** {avg_metrics['f1_score']:.3f}")
        report_lines.append(f"- **MRR:** {avg_metrics['mrr']:.3f}")
        report_lines.append(f"- **NDCG@10:** {avg_metrics['ndcg']:.3f}\n")

        report_lines.append("### Citation Accuracy")
        report_lines.append(f"- **Citation Accuracy:** {avg_metrics['citation_accuracy']:.3f}")
        report_lines.append(f"- **Supported Claims Ratio:** {avg_metrics['supported_claims_ratio']:.3f}")
        report_lines.append(f"- **Citation Quality Score:** {avg_metrics['citation_quality_score']:.3f}\n")

        report_lines.append("### Business Impact")
        report_lines.append(f"- **Avg Time Savings:** {avg_metrics['time_savings_minutes']:.1f} minutes")
        report_lines.append(f"- **Avg Cost Savings:** ${avg_metrics['cost_savings_dollars']:.2f}")
        report_lines.append(f"- **Accuracy Improvement:** {avg_metrics['accuracy_improvement']:.1%}\n")

        report_lines.append(f"### **Overall Quality Score: {avg_metrics['overall_quality_score']:.3f}**\n")

        # Individual test results
        report_lines.append("## Individual Test Results\n")

        for idx, result in enumerate(self.results, 1):
            report_lines.append(f"### Test {idx}: {result.test_id}")
            report_lines.append(f"**Query:** {result.query}")
            report_lines.append(f"**Timestamp:** {result.timestamp.isoformat()}\n")

            metrics_dict = result.metrics.to_dict()

            report_lines.append("**Metrics:**")
            report_lines.append(f"- Overall Quality: {metrics_dict['overall_quality_score']:.3f}")
            report_lines.append(f"- F1 Score: {metrics_dict['retrieval_quality']['f1_score']:.3f}")
            report_lines.append(f"- Citation Accuracy: {metrics_dict['citation_accuracy']['citation_accuracy']:.3f}")
            report_lines.append(f"- Time Savings: {metrics_dict['business_impact']['time_savings_minutes']:.1f} min\n")

            if result.notes:
                report_lines.append(f"**Notes:** {result.notes}\n")

        report = "\n".join(report_lines)

        # Save to file if specified
        if output_file:
            output_path = self.output_dir / output_file
            with open(output_path, "w") as f:
                f.write(report)

        return report

    def export_results_json(self, output_file: str = "evaluation_results.json"):
        """Export results to JSON file."""
        output_path = self.output_dir / output_file

        data = {
            "generated_at": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "aggregate_metrics": self._calculate_aggregate_metrics(),
            "results": [r.to_dict() for r in self.results]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        return str(output_path)

    def _calculate_aggregate_metrics(self) -> Dict[str, float]:
        """Calculate average metrics across all results."""
        if not self.results:
            return {}

        total = len(self.results)

        return {
            "precision": sum(r.metrics.precision for r in self.results) / total,
            "recall": sum(r.metrics.recall for r in self.results) / total,
            "f1_score": sum(r.metrics.f1_score for r in self.results) / total,
            "mrr": sum(r.metrics.mrr for r in self.results) / total,
            "ndcg": sum(r.metrics.ndcg for r in self.results) / total,
            "citation_accuracy": sum(r.metrics.citation_accuracy for r in self.results) / total,
            "supported_claims_ratio": sum(r.metrics.supported_claims_ratio for r in self.results) / total,
            "citation_quality_score": sum(r.metrics.citation_quality_score for r in self.results) / total,
            "time_savings_minutes": sum(r.metrics.time_savings_minutes for r in self.results) / total,
            "cost_savings_dollars": sum(r.metrics.cost_savings_dollars for r in self.results) / total,
            "accuracy_improvement": sum(r.metrics.accuracy_improvement for r in self.results) / total,
            "overall_quality_score": sum(r.metrics.overall_quality_score for r in self.results) / total
        }


# Helper function for running batch evaluations

async def run_evaluation_suite(
    orchestrator,
    test_cases: List[Dict[str, Any]],
    output_dir: str = "./evaluation_results"
) -> AgentEvaluator:
    """
    Run a suite of evaluation test cases.

    Args:
        orchestrator: OrchestratorAgent instance
        test_cases: List of test case dicts with query, ground_truth, etc.
        output_dir: Directory for results

    Returns:
        AgentEvaluator with results

    Example test_case:
        {
            "test_id": "test_001",
            "query": "What is the revenue of Company X?",
            "execution_pattern": "sequential",
            "ground_truth": {
                "relevant_documents": ["doc1.pdf", "doc2.pdf"],
                "expected_answer": "Expected answer text"
            },
            "notes": "Testing basic financial query"
        }
    """
    evaluator = AgentEvaluator(output_dir=output_dir)

    for test_case in test_cases:
        # Execute workflow
        result = await orchestrator.execute_workflow(
            user_query=test_case["query"],
            execution_pattern=test_case.get("execution_pattern", "sequential")
        )

        # Evaluate
        await evaluator.evaluate_workflow(
            test_id=test_case["test_id"],
            query=test_case["query"],
            workflow_result=result,
            ground_truth=test_case.get("ground_truth"),
            notes=test_case.get("notes", "")
        )

    # Generate report
    evaluator.generate_report("evaluation_report.md")
    evaluator.export_results_json("evaluation_results.json")

    return evaluator
