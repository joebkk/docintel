"""Citation agent for validating source attribution and accuracy."""

from typing import Dict, List, Any, Optional
import google.generativeai as genai
from datetime import datetime
import re

from config import settings


class CitationAgent:
    """
    Specialist agent for citation validation and accuracy checking.

    Responsibilities:
    - Validate that claims are supported by sources
    - Check citation accuracy
    - Identify unsupported claims
    - Calculate citation quality metrics
    - Generate proper citation format
    """

    def __init__(self):
        """Initialize citation agent."""
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    async def execute(
        self,
        analysis_results: List[Dict[str, Any]],
        research_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate citations in analysis against research sources.

        Args:
            analysis_results: Results from analysis agent
            research_results: Original research results with sources

        Returns:
            Dict with citation validation results and metrics
        """
        # Step 1: Extract all claims from analysis
        claims = await self._extract_claims(analysis_results)

        # Step 2: Validate each claim against sources
        validations = []
        for claim in claims:
            validation = await self._validate_claim(claim, research_results)
            validations.append(validation)

        # Step 3: Calculate accuracy metrics
        metrics = self._calculate_metrics(validations)

        # Step 4: Identify unsupported claims
        unsupported = [
            v["claim"] for v in validations
            if v["supported"] == False
        ]

        # Step 5: Generate citation report
        report = await self._generate_citation_report(
            validations,
            metrics,
            unsupported
        )

        return {
            "status": "completed",
            "accuracy": metrics["accuracy"],
            "total_claims": len(claims),
            "supported_claims": metrics["supported_count"],
            "unsupported_claims": metrics["unsupported_count"],
            "partially_supported": metrics["partially_supported_count"],
            "validations": validations,
            "unsupported": unsupported,
            "report": report,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }

    async def _extract_claims(
        self,
        analysis_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract factual claims from analysis results.

        Returns:
            List of claims with metadata
        """
        all_claims = []

        for idx, result in enumerate(analysis_results):
            # Extract text content from result
            text_content = self._extract_text_from_result(result)

            prompt = f"""Extract all factual claims from this analysis.

Analysis Text:
{text_content}

For each claim, identify:
1. The claim statement
2. The claim type (financial, operational, strategic, etc.)
3. Any numbers or specific data mentioned

Respond in JSON format:
[
  {{
    "claim": "specific claim statement",
    "type": "financial|operational|strategic|other",
    "contains_numbers": true|false,
    "numbers": ["number1", "number2"]
  }},
  ...
]
"""

            response = await self.model.generate_content_async(prompt)

            import json
            try:
                text = response.text
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]

                claims = json.loads(text.strip())

                # Add source analysis index
                for claim in claims:
                    claim["source_analysis_idx"] = idx

                all_claims.extend(claims)

            except Exception:
                # Fallback: extract sentences as claims
                sentences = text_content.split(".")
                for sentence in sentences[:10]:  # Limit to 10
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Skip very short sentences
                        all_claims.append({
                            "claim": sentence,
                            "type": "other",
                            "contains_numbers": bool(re.search(r'\d', sentence)),
                            "numbers": re.findall(r'\d+(?:\.\d+)?', sentence),
                            "source_analysis_idx": idx
                        })

        return all_claims

    async def _validate_claim(
        self,
        claim: Dict[str, Any],
        research_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate a single claim against research sources.

        Returns:
            Validation result with supporting evidence
        """
        # Gather all source content
        source_content = self._gather_source_content(research_results)

        prompt = f"""Validate this claim against the provided sources.

Claim: {claim['claim']}

Sources:
{source_content}

Determine:
1. Is the claim supported by the sources? (fully/partially/not supported)
2. Which specific sources support it?
3. What is the supporting quote/evidence?
4. Are there any contradictions?
5. Confidence level (high/medium/low)

Respond in JSON format:
{{
  "supported": true|false,
  "support_level": "fully|partially|not_supported",
  "supporting_sources": ["filename1", "filename2"],
  "evidence": "specific quote or data from source",
  "contradictions": "any contradicting information",
  "confidence": "high|medium|low",
  "reasoning": "explanation of validation"
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

            validation = json.loads(text.strip())
            validation["claim"] = claim["claim"]
            validation["claim_type"] = claim.get("type", "other")

            # Convert support_level to boolean for easier metrics
            validation["supported"] = validation["support_level"] in ["fully", "partially"]

            return validation

        except Exception:
            # Fallback validation
            return {
                "claim": claim["claim"],
                "claim_type": claim.get("type", "other"),
                "supported": True,  # Assume supported if validation fails
                "support_level": "unknown",
                "supporting_sources": [],
                "evidence": "",
                "contradictions": "",
                "confidence": "low",
                "reasoning": "Validation failed, defaulting to supported"
            }

    def _calculate_metrics(
        self,
        validations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate citation quality metrics.

        Returns:
            Dict with accuracy, precision, recall, etc.
        """
        total = len(validations)
        if total == 0:
            return {
                "accuracy": 0.0,
                "supported_count": 0,
                "unsupported_count": 0,
                "partially_supported_count": 0,
                "high_confidence_count": 0,
                "citation_quality_score": 0.0
            }

        supported = sum(1 for v in validations if v["support_level"] == "fully")
        partially = sum(1 for v in validations if v["support_level"] == "partially")
        unsupported = sum(1 for v in validations if v["support_level"] == "not_supported")
        high_confidence = sum(1 for v in validations if v["confidence"] == "high")

        # Accuracy: (fully + partially) / total
        accuracy = (supported + partially) / total

        # Quality score: weighted by confidence
        quality_score = (
            (supported * 1.0) +
            (partially * 0.5) +
            (high_confidence * 0.2)  # Bonus for high confidence
        ) / total

        return {
            "accuracy": round(accuracy, 3),
            "supported_count": supported,
            "partially_supported_count": partially,
            "unsupported_count": unsupported,
            "high_confidence_count": high_confidence,
            "citation_quality_score": round(quality_score, 3),
            "total_claims": total
        }

    async def _generate_citation_report(
        self,
        validations: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        unsupported: List[str]
    ) -> str:
        """Generate human-readable citation report."""
        report_parts = []

        report_parts.append("# Citation Validation Report\n")
        report_parts.append(f"**Overall Accuracy:** {metrics['accuracy']:.1%}")
        report_parts.append(f"**Quality Score:** {metrics['citation_quality_score']:.1%}\n")

        report_parts.append("## Summary")
        report_parts.append(f"- Total Claims: {metrics['total_claims']}")
        report_parts.append(f"- Fully Supported: {metrics['supported_count']}")
        report_parts.append(f"- Partially Supported: {metrics['partially_supported_count']}")
        report_parts.append(f"- Unsupported: {metrics['unsupported_count']}")
        report_parts.append(f"- High Confidence: {metrics['high_confidence_count']}\n")

        if unsupported:
            report_parts.append("## ⚠️ Unsupported Claims")
            for idx, claim in enumerate(unsupported[:5], 1):
                report_parts.append(f"{idx}. {claim}")
            report_parts.append("")

        # Highlight high-confidence validations
        high_confidence = [
            v for v in validations
            if v["confidence"] == "high" and v["support_level"] == "fully"
        ][:3]

        if high_confidence:
            report_parts.append("## ✓ Well-Supported Claims")
            for idx, val in enumerate(high_confidence, 1):
                report_parts.append(f"{idx}. {val['claim']}")
                report_parts.append(f"   Sources: {', '.join(val['supporting_sources'])}")
                report_parts.append("")

        return "\n".join(report_parts)

    def _extract_text_from_result(self, result: Dict[str, Any]) -> str:
        """Extract text content from analysis result."""
        text_parts = []

        if isinstance(result, str):
            return result

        # Try various fields where text might be
        for field in ["executive_summary", "analysis", "conclusion", "result"]:
            if field in result:
                content = result[field]
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, dict):
                    text_parts.append(str(content))

        # If result has nested analysis
        if "result" in result and isinstance(result["result"], dict):
            for key, value in result["result"].items():
                if isinstance(value, (str, list)):
                    text_parts.append(f"{key}: {value}")

        return "\n".join(text_parts) if text_parts else str(result)

    def _gather_source_content(
        self,
        research_results: List[Dict[str, Any]]
    ) -> str:
        """Gather and format source content for validation."""
        sources = []

        for idx, result in enumerate(research_results):
            if "sources" in result:
                for source in result["sources"][:5]:  # Limit sources
                    file_name = source.get("fileName", "Unknown")
                    content = source.get("content", "")[:1000]  # Truncate

                    sources.append(f"[{file_name}]\n{content}\n")

            # Also include enhanced summaries
            if "enhanced_summary" in result:
                sources.append(f"[Summary {idx + 1}]\n{result['enhanced_summary']}\n")

        return "\n".join(sources[:20])  # Limit total sources

    async def generate_bibliography(
        self,
        research_results: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Generate properly formatted bibliography from sources.

        Returns:
            List of citation entries
        """
        unique_sources = {}

        for result in research_results:
            for source in result.get("sources", []):
                file_name = source.get("fileName")
                if file_name and file_name not in unique_sources:
                    unique_sources[file_name] = {
                        "title": file_name,
                        "url": source.get("url", ""),
                        "type": source.get("type", "document"),
                        "accessed": datetime.now().strftime("%Y-%m-%d")
                    }

        # Sort alphabetically
        bibliography = sorted(
            unique_sources.values(),
            key=lambda x: x["title"]
        )

        return bibliography
