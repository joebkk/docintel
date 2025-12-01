"""Research agent for document retrieval and information gathering."""

from typing import Dict, List, Any, Optional
import google.generativeai as genai

from config import settings
from tools.rag_openapi_tool import RAGOpenAPITool


class ResearchAgent:
    """
    Specialist agent for research and information retrieval.

    Responsibilities:
    - Query the RAG system for relevant documents
    - Extract key information from sources
    - Summarize findings
    - Identify information gaps
    """

    def __init__(self):
        """Initialize research agent."""
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.rag_tool = RAGOpenAPITool()

    async def execute(
        self,
        query: str,
        mode: str = "hybrid",
        file_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute research task.

        Args:
            query: Research question
            mode: Search mode (hybrid, semantic, lexical)
            file_names: Optional filter for specific files

        Returns:
            Dict with research results, sources, and summary
        """
        # Query RAG system
        # print(f"DEBUG: query={query}, mode={mode}")  # TODO: remove debug
        rag_result = await self.rag_tool.search_documents(
            query=query,
            mode=mode,
            file_names=file_names
        )

        if "error" in rag_result:
            return {
                "status": "error",
                "query": query,
                "error": rag_result["error"],
                "sources": [],
                "summary": None
            }

        sources = rag_result.get("sources", [])
        rag_answer = rag_result.get("answer", "")

        # Step 2: Enhance with LLM analysis
        enhanced_summary = await self._enhance_summary(
            query=query,
            sources=sources,
            rag_answer=rag_answer
        )

        # Step 3: Extract key facts
        key_facts = await self._extract_key_facts(sources, rag_answer)

        # Step 4: Identify information gaps
        gaps = await self._identify_gaps(query, sources, key_facts)

        return {
            "status": "completed",
            "query": query,
            "sources": sources,
            "raw_answer": rag_answer,
            "enhanced_summary": enhanced_summary,
            "key_facts": key_facts,
            "information_gaps": gaps,
            "metadata": {
                "num_sources": len(sources),
                "search_mode": mode,
                "file_names": file_names
            }
        }

    async def _enhance_summary(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        rag_answer: str
    ) -> str:
        """
        Use LLM to enhance the RAG answer with better structure.

        Args:
            query: Original query
            sources: Retrieved source documents
            rag_answer: Raw answer from RAG system

        Returns:
            Enhanced summary with better organization
        """
        source_summaries = self._format_sources(sources)

        prompt = f"""You are a research analyst reviewing document retrieval results.

Query: {query}

RAG System Answer:
{rag_answer}

Source Documents:
{source_summaries}

Provide an enhanced summary that:
1. Clearly answers the query
2. Organizes information logically
3. Highlights the most important findings
4. Notes any contradictions or uncertainties
5. References specific sources

Enhanced Summary:
"""

        response = await self.model.generate_content_async(prompt)
        return response.text

    async def _extract_key_facts(
        self,
        sources: List[Dict[str, Any]],
        rag_answer: str
    ) -> List[Dict[str, str]]:
        """
        Extract key facts with source attribution.

        Returns:
            List of facts with citations
        """
        source_summaries = self._format_sources(sources)

        prompt = f"""Extract key facts from the following information.

Answer: {rag_answer}

Sources: {source_summaries}

For each fact, provide:
1. The fact statement
2. The source document(s)
3. Confidence level (high/medium/low)

Respond in JSON format:
[
  {{
    "fact": "specific fact statement",
    "sources": ["filename1", "filename2"],
    "confidence": "high|medium|low",
    "quote": "relevant quote from source"
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

            facts = json.loads(text.strip())
            return facts
        except Exception:
            # Fallback to simple extraction
            return [{
                "fact": rag_answer[:200],
                "sources": [s.get("fileName", "unknown") for s in sources[:3]],
                "confidence": "medium",
                "quote": ""
            }]

    async def _identify_gaps(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        key_facts: List[Dict[str, str]]
    ) -> List[str]:
        """
        Identify information gaps that need additional research.

        Returns:
            List of gap descriptions
        """
        prompt = f"""Analyze the research results for information gaps.

Original Query: {query}

Number of Sources: {len(sources)}
Key Facts Found: {len(key_facts)}

Facts Summary:
{[f["fact"] for f in key_facts[:5]]}

Identify what important information is missing or unclear.
List 3-5 specific gaps that would improve the answer.

Gaps:
"""

        response = await self.model.generate_content_async(prompt)

        # Parse gaps from response
        gaps = []
        for line in response.text.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                # Remove numbering/bullets
                gap = line.lstrip("0123456789.-* ")
                if gap:
                    gaps.append(gap)

        return gaps[:5]  # Limit to 5 gaps

    def _format_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Format sources for LLM prompts."""
        formatted = []

        for idx, source in enumerate(sources[:10]):  # Limit to top 10
            file_name = source.get("fileName", "Unknown")
            content = source.get("content", "")[:500]  # Truncate
            score = source.get("score", 0.0)

            formatted.append(
                f"[{idx + 1}] {file_name} (relevance: {score:.2f})\n{content}...\n"
            )

        return "\n".join(formatted)

    async def close(self):
        """Cleanup resources."""
        await self.rag_tool.close()
