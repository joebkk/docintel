"""OpenAPI tool for RAG backend integration."""

import httpx
import json
from typing import Dict, List, Any
from config import settings


class RAGOpenAPITool:
    """
    OpenAPI integration with TypeScript RAG backend.

    This tool allows agents to search documents using the existing
    RAG system's unified-search and ai-chat endpoints.
    """

    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.rag_api_url
        self.api_key = settings.rag_api_key
        self.client = httpx.AsyncClient(timeout=60.0)

    async def search_documents(
        self,
        query: str,
        mode: str = "hybrid",
        file_names: List[str] | None = None
    ) -> Dict[str, Any]:
        """
        Search across documents using hybrid search.

        Args:
            query: Search query string
            mode: Search mode - "lexical", "semantic", or "hybrid"
            file_names: Optional list of filenames to filter

        Returns:
            Dict with search results including sources and AI-generated answer
        """
        url = f"{self.base_url}/api/unified-search"

        payload = {
            "query": query,
            "mode": mode
        }

        if file_names:
            payload["fileNames"] = file_names

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            # Parse SSE stream
            result = self._parse_sse_response(response.text)
            return result

        except httpx.HTTPError as e:
            return {
                "error": str(e),
                "query": query,
                "mode": mode
            }

    async def chat_with_document(
        self,
        messages: List[Dict[str, str]],
        file_name: str | None = None,
        document_key: str | None = None
    ) -> Dict[str, Any]:
        """
        Conversational Q&A with specific document.

        Args:
            messages: List of message objects with role and content
            file_name: Optional filename to scope search
            document_key: Optional document key

        Returns:
            Dict with chat response
        """
        url = f"{self.base_url}/api/ai-chat"

        payload = {"messages": messages}

        if file_name:
            payload["fileName"] = file_name
        if document_key:
            payload["documentKey"] = document_key

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = self._parse_sse_response(response.text)
            return result

        except httpx.HTTPError as e:
            return {
                "error": str(e),
                "messages": messages
            }

    def _parse_sse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response."""
        result = {
            "metadata": {},
            "sources": [],
            "answer": ""
        }

        for line in response_text.split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])

                    if data.get("type") == "metadata":
                        result["metadata"] = data
                    elif data.get("type") == "sources":
                        result["sources"] = data.get("sources", [])
                    elif data.get("type") == "text":
                        result["answer"] += data.get("content", "")

                except json.JSONDecodeError:
                    continue

        return result

    @staticmethod
    def get_openapi_spec_path() -> str:
        """Return path to OpenAPI specification."""
        return "docs/rag-openapi.yaml"

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
