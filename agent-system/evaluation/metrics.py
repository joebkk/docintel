"""Evaluation metrics for agent performance assessment."""

from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
import math


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""

    # Retrieval quality metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain

    # Citation accuracy metrics
    citation_accuracy: float = 0.0
    supported_claims_ratio: float = 0.0
    citation_quality_score: float = 0.0

    # Business impact metrics
    time_savings_minutes: float = 0.0
    cost_savings_dollars: float = 0.0
    accuracy_improvement: float = 0.0

    # Overall scores
    overall_quality_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "retrieval_quality": {
                "precision": round(self.precision, 3),
                "recall": round(self.recall, 3),
                "f1_score": round(self.f1_score, 3),
                "mrr": round(self.mrr, 3),
                "ndcg": round(self.ndcg, 3)
            },
            "citation_accuracy": {
                "citation_accuracy": round(self.citation_accuracy, 3),
                "supported_claims_ratio": round(self.supported_claims_ratio, 3),
                "citation_quality_score": round(self.citation_quality_score, 3)
            },
            "business_impact": {
                "time_savings_minutes": round(self.time_savings_minutes, 1),
                "cost_savings_dollars": round(self.cost_savings_dollars, 2),
                "accuracy_improvement": round(self.accuracy_improvement, 3)
            },
            "overall_quality_score": round(self.overall_quality_score, 3)
        }


def calculate_precision_recall(
    retrieved: List[str],
    relevant: List[str]
) -> Tuple[float, float, float]:
    """
    Calculate precision, recall, and F1 score.

    Args:
        retrieved: List of retrieved document IDs
        relevant: List of ground-truth relevant document IDs

    Returns:
        Tuple of (precision, recall, f1_score)
    """
    if not retrieved:
        return 0.0, 0.0, 0.0

    retrieved_set = set(retrieved)
    relevant_set = set(relevant)

    true_positives = len(retrieved_set & relevant_set)

    precision = true_positives / len(retrieved_set) if retrieved_set else 0.0
    recall = true_positives / len(relevant_set) if relevant_set else 0.0

    if precision + recall > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0.0

    return precision, recall, f1_score


def calculate_mrr(
    retrieved_lists: List[List[str]],
    relevant_lists: List[List[str]]
) -> float:
    """
    Calculate Mean Reciprocal Rank.

    MRR measures how high the first relevant document appears
    in the ranked list.

    Args:
        retrieved_lists: List of ranked retrieval results (one per query)
        relevant_lists: List of relevant documents (one per query)

    Returns:
        MRR score (0.0 to 1.0)
    """
    if not retrieved_lists or not relevant_lists:
        return 0.0

    reciprocal_ranks = []

    for retrieved, relevant in zip(retrieved_lists, relevant_lists):
        relevant_set = set(relevant)

        # Find rank of first relevant document
        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant_set:
                reciprocal_ranks.append(1.0 / rank)
                break
        else:
            # No relevant document found
            reciprocal_ranks.append(0.0)

    return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0


def calculate_ndcg(
    retrieved: List[str],
    relevant: List[str],
    k: int = 10
) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain at k.

    NDCG measures ranking quality, giving higher scores when
    relevant documents appear earlier in the list.

    Args:
        retrieved: Ranked list of retrieved document IDs
        relevant: List of relevant document IDs
        k: Cutoff rank

    Returns:
        NDCG@k score (0.0 to 1.0)
    """
    if not retrieved or not relevant:
        return 0.0

    relevant_set = set(relevant)

    # Calculate DCG@k
    dcg = 0.0
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant_set:
            # rel = 1 for relevant, 0 for non-relevant
            dcg += 1.0 / math.log2(rank + 1)

    # Calculate ideal DCG@k (all relevant docs at top)
    idcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, min(len(relevant), k) + 1)
    )

    return dcg / idcg if idcg > 0 else 0.0


def calculate_retrieval_metrics(
    retrieved_documents: List[str],
    relevant_documents: List[str],
    k: int = 10
) -> Dict[str, float]:
    """
    Calculate comprehensive retrieval quality metrics.

    Args:
        retrieved_documents: Retrieved document IDs
        relevant_documents: Ground-truth relevant document IDs
        k: Cutoff for NDCG calculation

    Returns:
        Dict with precision, recall, F1, NDCG
    """
    precision, recall, f1 = calculate_precision_recall(
        retrieved_documents,
        relevant_documents
    )

    ndcg = calculate_ndcg(retrieved_documents, relevant_documents, k)

    # MRR requires list of lists, so wrap in single-item lists
    mrr = calculate_mrr([retrieved_documents], [relevant_documents])

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "mrr": mrr,
        "ndcg": ndcg
    }


def calculate_citation_accuracy(
    claims: List[Dict[str, Any]],
    validations: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate citation accuracy metrics.

    Args:
        claims: List of extracted claims
        validations: List of citation validations

    Returns:
        Dict with accuracy, support ratio, quality score
    """
    if not validations:
        return {
            "citation_accuracy": 0.0,
            "supported_claims_ratio": 0.0,
            "citation_quality_score": 0.0
        }

    total = len(validations)

    # Count fully supported, partially supported, unsupported
    fully_supported = sum(
        1 for v in validations
        if v.get("support_level") == "fully"
    )

    partially_supported = sum(
        1 for v in validations
        if v.get("support_level") == "partially"
    )

    unsupported = sum(
        1 for v in validations
        if v.get("support_level") == "not_supported"
    )

    # High confidence validations
    high_confidence = sum(
        1 for v in validations
        if v.get("confidence") == "high"
    )

    # Accuracy: (fully + partially) / total
    accuracy = (fully_supported + partially_supported) / total

    # Support ratio: fully / total
    support_ratio = fully_supported / total

    # Quality score: weighted by support level and confidence
    quality_score = (
        (fully_supported * 1.0) +
        (partially_supported * 0.5) +
        (high_confidence * 0.2)  # Bonus for high confidence
    ) / total

    return {
        "citation_accuracy": accuracy,
        "supported_claims_ratio": support_ratio,
        "citation_quality_score": quality_score,
        "total_claims": total,
        "fully_supported": fully_supported,
        "partially_supported": partially_supported,
        "unsupported": unsupported,
        "high_confidence": high_confidence
    }


def calculate_business_impact(
    execution_duration_seconds: float,
    num_documents_analyzed: int,
    num_claims_validated: int,
    citation_accuracy: float
) -> Dict[str, float]:
    """
    Calculate business impact metrics for PE/VC context.

    Estimates time and cost savings compared to manual analysis.

    Args:
        execution_duration_seconds: Time taken by agent system
        num_documents_analyzed: Number of documents processed
        num_claims_validated: Number of claims validated
        citation_accuracy: Citation accuracy score

    Returns:
        Dict with time savings, cost savings, accuracy improvement
    """
    # Assumptions for PE/VC manual analysis
    MINUTES_PER_DOCUMENT_MANUAL = 15  # Manual doc review
    MINUTES_PER_CLAIM_MANUAL = 3      # Manual citation checking
    HOURLY_RATE_ANALYST = 150         # USD per hour

    # Calculate manual time
    manual_minutes = (
        (num_documents_analyzed * MINUTES_PER_DOCUMENT_MANUAL) +
        (num_claims_validated * MINUTES_PER_CLAIM_MANUAL)
    )

    # Agent time in minutes
    agent_minutes = execution_duration_seconds / 60

    # Time savings
    time_savings = max(0, manual_minutes - agent_minutes)

    # Cost savings (time saved * hourly rate)
    cost_savings = (time_savings / 60) * HOURLY_RATE_ANALYST

    # Accuracy improvement estimate
    # Assume manual citation checking is ~80% accurate (human error)
    # Agent with high citation accuracy can improve this
    manual_accuracy = 0.80
    accuracy_improvement = max(0, citation_accuracy - manual_accuracy)

    return {
        "time_savings_minutes": time_savings,
        "cost_savings_dollars": cost_savings,
        "accuracy_improvement": accuracy_improvement,
        "manual_time_minutes": manual_minutes,
        "agent_time_minutes": agent_minutes,
        "time_reduction_percentage": (time_savings / manual_minutes * 100) if manual_minutes > 0 else 0
    }


def calculate_overall_quality_score(metrics: EvaluationMetrics) -> float:
    """
    Calculate overall quality score from all metrics.

    Weighted combination of:
    - Retrieval quality (30%)
    - Citation accuracy (40%)
    - Business impact (30%)

    Args:
        metrics: EvaluationMetrics object

    Returns:
        Overall quality score (0.0 to 1.0)
    """
    # Retrieval quality composite (average of F1 and NDCG)
    retrieval_quality = (metrics.f1_score + metrics.ndcg) / 2

    # Citation quality
    citation_quality = metrics.citation_quality_score

    # Business impact (normalized time savings)
    # Assume 100 minutes saved is excellent (score 1.0)
    business_impact = min(metrics.time_savings_minutes / 100, 1.0)

    # Weighted average
    overall = (
        (retrieval_quality * 0.30) +
        (citation_quality * 0.40) +
        (business_impact * 0.30)
    )

    return overall


def compare_agent_runs(
    baseline_metrics: EvaluationMetrics,
    experiment_metrics: EvaluationMetrics
) -> Dict[str, Dict[str, float]]:
    """
    Compare two agent runs to measure improvement.

    Args:
        baseline_metrics: Metrics from baseline run
        experiment_metrics: Metrics from experiment run

    Returns:
        Dict with absolute and percentage improvements
    """
    def calc_improvement(baseline: float, experiment: float) -> Dict[str, float]:
        absolute = experiment - baseline
        percentage = (absolute / baseline * 100) if baseline > 0 else 0.0

        return {
            "baseline": baseline,
            "experiment": experiment,
            "absolute_improvement": absolute,
            "percentage_improvement": percentage
        }

    return {
        "precision": calc_improvement(
            baseline_metrics.precision,
            experiment_metrics.precision
        ),
        "recall": calc_improvement(
            baseline_metrics.recall,
            experiment_metrics.recall
        ),
        "f1_score": calc_improvement(
            baseline_metrics.f1_score,
            experiment_metrics.f1_score
        ),
        "citation_accuracy": calc_improvement(
            baseline_metrics.citation_accuracy,
            experiment_metrics.citation_accuracy
        ),
        "overall_quality": calc_improvement(
            baseline_metrics.overall_quality_score,
            experiment_metrics.overall_quality_score
        )
    }
