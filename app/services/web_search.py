import logging

import httpx
from pydantic import ValidationError

from app.config import Settings, is_placeholder_value
from app.schemas import ResearchResults, SearchResult

logger = logging.getLogger(__name__)
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class SearchServiceError(RuntimeError):
    pass


class WebSearchService:
    def __init__(self, settings: Settings) -> None:
        if not settings.search_api_key or is_placeholder_value(settings.search_api_key):
            raise SearchServiceError(
                "SEARCH_API_KEY is not configured correctly. Replace the placeholder value in .env with a real Tavily API key."
            )
        self._api_key = settings.search_api_key
        self._timeout = settings.search_timeout_seconds

    def search(self, topic: str) -> ResearchResults:
        try:
            response = httpx.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": self._api_key,
                    "query": topic,
                    "search_depth": "basic",
                    "max_results": 8,
                    "include_answer": False,
                },
                timeout=self._timeout,
            )
            if response.status_code == 429:
                raise SearchServiceError("The web search service rate limit was reached.")
            response.raise_for_status()
            payload = response.json()
        except SearchServiceError:
            raise
        except httpx.TimeoutException as exc:
            logger.warning("Web search timed out")
            raise SearchServiceError("The web search request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Web search returned HTTP %s", exc.response.status_code)
            raise SearchServiceError("The web search service returned an error.") from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Web search request failed: %s", exc)
            raise SearchServiceError("The web search request failed.") from exc

        sources = []
        for result in payload.get("results", []):
            try:
                sources.append(
                    SearchResult(
                        source_id=f"S{len(sources) + 1}",
                        title=result.get("title") or "Untitled source",
                        url=result["url"],
                        snippet=result.get("content") or "",
                    )
                )
            except (KeyError, ValidationError):
                continue

        if not sources:
            raise SearchServiceError("No useful web search results were found for this topic.")
        return ResearchResults(topic=topic, sources=sources)
