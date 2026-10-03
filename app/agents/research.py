import logging

from app.schemas import ResearchResults
from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self, search_service: WebSearchService) -> None:
        self._search_service = search_service

    def run(self, topic: str) -> ResearchResults:
        logger.info("Agent 1 Web Research started")
        try:
            results = self._search_service.search(topic)
            logger.info("Agent 1 Web Research completed (%s sources)", len(results.sources))
            return results
        except Exception:
            logger.exception("Agent 1 Web Research failed")
            raise
