"""Custom enterprise tools for document intelligence."""

from typing import Dict, List, Any
from datetime import datetime, date
import json


def calculate_portfolio_metrics(
    companies: List[str],
    metric: str,
    timeframe: str,
    rag_tool: Any
) -> Dict[str, Any]:
    """
    Calculate aggregated metrics across portfolio companies.

    This custom tool demonstrates enterprise workflow automation
    by aggregating data across multiple companies.

    Args:
        companies: List of company names
        metric: Metric to calculate (revenue, growth, risks, etc.)
        timeframe: Time period (Q1, Q2, Q3, Q4, 2024, etc.)
        rag_tool: RAG tool instance for searching

    Returns:
        Dict with metric calculations for each company and aggregate
    """
    results = {}

    for company in companies:
        # Search for metric in company-specific documents
        query = f"{company} {metric} {timeframe}"

        # Use RAG to find relevant information
        search_result = rag_tool.search_documents(
            query=query,
            mode="hybrid",
            file_names=[f"{company}*.pdf", f"*{company}*.pdf"]
        )

        results[company] = {
            "metric": metric,
            "timeframe": timeframe,
            "data": search_result.get("answer", ""),
            "sources": search_result.get("sources", []),
            "confidence": len(search_result.get("sources", [])) > 0
        }

    # Calculate aggregate statistics
    total_companies = len(companies)
    companies_with_data = sum(1 for r in results.values() if r["confidence"])

    return {
        "metric": metric,
        "timeframe": timeframe,
        "total_companies": total_companies,
        "companies_with_data": companies_with_data,
        "coverage": companies_with_data / total_companies if total_companies > 0 else 0,
        "results": results,
        "generated_at": datetime.utcnow().isoformat()
    }


def generate_compliance_report(
    analyst_id: str,
    start_date: str,
    end_date: str,
    mongodb_client: Any
) -> Dict[str, Any]:
    """
    Generate compliance audit report for enterprise governance.

    This demonstrates enterprise observability and audit trail
    requirements for regulatory compliance.

    Args:
        analyst_id: Analyst user ID
        start_date: Report start date (YYYY-MM-DD)
        end_date: Report end date (YYYY-MM-DD)
        mongodb_client: MongoDB client for accessing audit logs

    Returns:
        Dict with compliance report data
    """
    # Parse dates
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    # Query audit logs from MongoDB
    # (Assuming agent interactions are logged in agent_memory collection)
    db = mongodb_client[settings.mongodb_database]
    collection = db.get_collection("processing_history")

    # Find all analyst queries in date range
    query_filter = {
        "analyst_id": analyst_id,
        "timestamp": {
            "$gte": start,
            "$lte": end
        }
    }

    audit_logs = list(collection.find(query_filter).sort("timestamp", 1))

    # Aggregate statistics
    total_queries = len(audit_logs)
    unique_documents = set()
    unique_topics = set()

    for log in audit_logs:
        if "documents" in log:
            unique_documents.update(log["documents"])
        if "topic" in log:
            unique_topics.add(log["topic"])

    return {
        "analyst_id": analyst_id,
        "period": {
            "start": start_date,
            "end": end_date
        },
        "statistics": {
            "total_queries": total_queries,
            "unique_documents_accessed": len(unique_documents),
            "unique_topics_researched": len(unique_topics),
            "avg_queries_per_day": total_queries / ((end - start).days + 1)
        },
        "documents_accessed": list(unique_documents),
        "topics_researched": list(unique_topics),
        "audit_trail": [
            {
                "timestamp": log.get("timestamp", "").isoformat(),
                "query": log.get("query", ""),
                "documents": log.get("documents", []),
                "operation": log.get("operation", "")
            }
            for log in audit_logs
        ],
        "generated_at": datetime.utcnow().isoformat(),
        "compliance_status": "compliant" if total_queries > 0 else "no_activity"
    }


def extract_key_findings(
    documents: List[str],
    topic: str,
    rag_tool: Any
) -> Dict[str, Any]:
    """
    Extract key findings across multiple documents on a specific topic.

    Args:
        documents: List of document filenames
        topic: Topic to extract findings about
        rag_tool: RAG tool instance

    Returns:
        Dict with extracted findings
    """
    findings = []

    for doc in documents:
        result = rag_tool.search_documents(
            query=f"{topic} key findings summary",
            mode="semantic",
            file_names=[doc]
        )

        if result.get("sources"):
            findings.append({
                "document": doc,
                "finding": result.get("answer", ""),
                "sources": result.get("sources", []),
                "relevance_score": len(result.get("sources", []))
            })

    # Sort by relevance
    findings.sort(key=lambda x: x["relevance_score"], reverse=True)

    return {
        "topic": topic,
        "total_documents": len(documents),
        "documents_with_findings": len(findings),
        "findings": findings,
        "summary": _synthesize_findings(findings) if findings else "No findings extracted",
        "generated_at": datetime.utcnow().isoformat()
    }


def _synthesize_findings(findings: List[Dict]) -> str:
    """Synthesize multiple findings into a summary."""
    if not findings:
        return ""

    # Simple synthesis - in production, use LLM for better synthesis
    synthesis = f"Analysis of {len(findings)} documents revealed:\n\n"

    for i, finding in enumerate(findings[:5], 1):  # Top 5 findings
        synthesis += f"{i}. From {finding['document']}:\n"
        synthesis += f"   {finding['finding'][:200]}...\n\n"

    return synthesis


# Tool registry for easy access
CUSTOM_TOOLS = {
    "calculate_portfolio_metrics": calculate_portfolio_metrics,
    "generate_compliance_report": generate_compliance_report,
    "extract_key_findings": extract_key_findings,
}
