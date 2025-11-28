"""Analysis agent for processing and analyzing research results."""

from typing import Dict, List, Any, Optional
import google.generativeai as genai
from datetime import datetime

from config import settings


class AnalysisAgent:
    """
    Specialist agent for data analysis and insight generation.

    Responsibilities:
    - Analyze research results
    - Extract patterns and trends
    - Generate insights for PE/VC context
    - Calculate business metrics
    - Compare across companies/deals
    """

    def __init__(self):
        """Initialize analysis agent."""
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    async def execute(
        self,
        analysis_task: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute analysis task.

        Args:
            analysis_task: Description of analysis to perform
            context: Research results to analyze

        Returns:
            Dict with analysis results and insights
        """
        if not context:
            return {
                "status": "error",
                "error": "No context provided for analysis",
                "task": analysis_task
            }

        # Step 1: Determine analysis type
        analysis_type = await self._classify_analysis_type(analysis_task)

        # Step 2: Execute appropriate analysis
        if analysis_type == "financial":
            result = await self._analyze_financial(analysis_task, context)
        elif analysis_type == "comparative":
            result = await self._analyze_comparative(analysis_task, context)
        elif analysis_type == "trend":
            result = await self._analyze_trends(analysis_task, context)
        elif analysis_type == "risk":
            result = await self._analyze_risk(analysis_task, context)
        else:
            result = await self._analyze_general(analysis_task, context)

        # Step 3: Generate executive summary
        executive_summary = await self._generate_executive_summary(
            analysis_task,
            result
        )

        return {
            "status": "completed",
            "task": analysis_task,
            "analysis_type": analysis_type,
            "result": result,
            "executive_summary": executive_summary,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "num_sources_analyzed": len(context)
            }
        }

    async def _classify_analysis_type(self, analysis_task: str) -> str:
        """
        Classify the type of analysis needed.

        Returns:
            Analysis type: financial, comparative, trend, risk, or general
        """
        prompt = f"""Classify this analysis task into one category:

Task: {analysis_task}

Categories:
- financial: Revenue, profit, valuation, returns, financial metrics
- comparative: Comparing multiple companies, deals, or time periods
- trend: Identifying patterns over time or across portfolio
- risk: Risk assessment, due diligence, compliance
- general: Other types of analysis

Respond with only the category name.
"""

        response = await self.model.generate_content_async(prompt)
        classification = response.text.strip().lower()

        valid_types = ["financial", "comparative", "trend", "risk", "general"]
        return classification if classification in valid_types else "general"

    async def _analyze_financial(
        self,
        task: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform financial analysis."""
        # Extract financial data from context
        financial_data = self._extract_data_from_context(context)

        prompt = f"""Perform financial analysis on the following data:

Task: {task}

Data:
{financial_data}

Provide:
1. Key financial metrics identified
2. Calculations and formulas used
3. Trends or patterns
4. Benchmarking (if applicable)
5. Recommendations

Respond in JSON format:
{{
  "metrics": {{"metric_name": value}},
  "calculations": [{{"name": "calc", "formula": "formula", "result": value}}],
  "trends": ["trend1", "trend2"],
  "insights": ["insight1", "insight2"],
  "recommendations": ["rec1", "rec2"]
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

            analysis = json.loads(text.strip())
            return analysis
        except Exception:
            return {
                "metrics": {},
                "calculations": [],
                "trends": [],
                "insights": [response.text],
                "recommendations": []
            }

    async def _analyze_comparative(
        self,
        task: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform comparative analysis across entities."""
        data = self._extract_data_from_context(context)

        prompt = f"""Perform comparative analysis:

Task: {task}

Data:
{data}

Provide:
1. Entities being compared
2. Comparison dimensions/criteria
3. Key differences and similarities
4. Rankings or ratings
5. Conclusions

Respond in JSON format:
{{
  "entities": ["entity1", "entity2"],
  "comparison_dimensions": ["dimension1", "dimension2"],
  "differences": [{{"aspect": "X", "entity1": "Y", "entity2": "Z"}}],
  "similarities": ["similarity1"],
  "ranking": [{{"entity": "name", "rank": 1, "score": 0.9}}],
  "conclusion": "overall conclusion"
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

            analysis = json.loads(text.strip())
            return analysis
        except Exception:
            return {
                "entities": [],
                "comparison_dimensions": [],
                "differences": [],
                "similarities": [],
                "ranking": [],
                "conclusion": response.text
            }

    async def _analyze_trends(
        self,
        task: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze trends over time or across data."""
        data = self._extract_data_from_context(context)

        prompt = f"""Analyze trends in the data:

Task: {task}

Data:
{data}

Provide:
1. Identified trends (upward, downward, cyclical, etc.)
2. Time periods or segments
3. Rate of change
4. Anomalies or outliers
5. Projections (if appropriate)

Respond in JSON format:
{{
  "trends": [{{"name": "trend", "direction": "up|down|stable", "strength": "strong|moderate|weak"}}],
  "time_periods": ["period1", "period2"],
  "rate_of_change": {{"metric": "rate"}},
  "anomalies": ["anomaly1"],
  "projections": "future outlook"
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

            analysis = json.loads(text.strip())
            return analysis
        except Exception:
            return {
                "trends": [],
                "time_periods": [],
                "rate_of_change": {},
                "anomalies": [],
                "projections": response.text
            }

    async def _analyze_risk(
        self,
        task: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform risk assessment."""
        data = self._extract_data_from_context(context)

        prompt = f"""Perform risk analysis:

Task: {task}

Data:
{data}

Provide:
1. Identified risks
2. Risk categories (market, operational, financial, regulatory, etc.)
3. Severity assessment (high/medium/low)
4. Likelihood assessment
5. Mitigation recommendations

Respond in JSON format:
{{
  "risks": [
    {{
      "risk": "risk description",
      "category": "market|operational|financial|regulatory|other",
      "severity": "high|medium|low",
      "likelihood": "high|medium|low",
      "impact": "description",
      "mitigation": "recommendation"
    }}
  ],
  "overall_risk_level": "high|medium|low",
  "key_concerns": ["concern1", "concern2"]
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

            analysis = json.loads(text.strip())
            return analysis
        except Exception:
            return {
                "risks": [],
                "overall_risk_level": "unknown",
                "key_concerns": [response.text]
            }

    async def _analyze_general(
        self,
        task: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform general analysis."""
        data = self._extract_data_from_context(context)

        prompt = f"""Analyze the following:

Task: {task}

Data:
{data}

Provide comprehensive analysis including:
1. Key findings
2. Patterns or themes
3. Important details
4. Implications
5. Recommendations

Analysis:
"""

        response = await self.model.generate_content_async(prompt)

        return {
            "analysis": response.text,
            "key_findings": await self._extract_key_findings(response.text),
            "recommendations": await self._extract_recommendations(response.text)
        }

    async def _generate_executive_summary(
        self,
        task: str,
        result: Dict[str, Any]
    ) -> str:
        """Generate executive summary of analysis."""
        prompt = f"""Create an executive summary of this analysis.

Task: {task}

Analysis Results:
{result}

Provide a concise 2-3 paragraph executive summary that:
1. States the key finding upfront
2. Highlights the most important insights
3. Notes any critical recommendations or next steps

Executive Summary:
"""

        response = await self.model.generate_content_async(prompt)
        return response.text

    async def _extract_key_findings(self, analysis: str) -> List[str]:
        """Extract key findings from analysis text."""
        findings = []
        for line in analysis.split("\n"):
            line = line.strip()
            if line and (
                line.lower().startswith("key") or
                line.lower().startswith("finding") or
                line.lower().startswith("important") or
                (line[0].isdigit() and "." in line[:3])
            ):
                findings.append(line.lstrip("0123456789.-* "))

        return findings[:5]

    async def _extract_recommendations(self, analysis: str) -> List[str]:
        """Extract recommendations from analysis text."""
        recommendations = []
        in_recommendations = False

        for line in analysis.split("\n"):
            line = line.strip()

            if "recommendation" in line.lower():
                in_recommendations = True
                continue

            if in_recommendations and line and (
                line[0].isdigit() or
                line.startswith("-") or
                line.startswith("*")
            ):
                recommendations.append(line.lstrip("0123456789.-* "))

        return recommendations[:5]

    def _extract_data_from_context(
        self,
        context: List[Dict[str, Any]]
    ) -> str:
        """Extract and format data from research context."""
        formatted = []

        for idx, item in enumerate(context):
            if isinstance(item, dict):
                # Handle research results
                if "enhanced_summary" in item:
                    formatted.append(f"Source {idx + 1}:")
                    formatted.append(item["enhanced_summary"])
                elif "key_facts" in item:
                    formatted.append(f"Source {idx + 1} Facts:")
                    for fact in item["key_facts"][:3]:
                        formatted.append(f"  - {fact.get('fact', '')}")
                else:
                    formatted.append(f"Source {idx + 1}: {item}")

        return "\n".join(formatted)
