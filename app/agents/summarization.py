import json
import logging

from app.schemas import ResearchResults, ResearchSummary
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)


class SummarizationAgent:
    def __init__(self, llm: GroqClient) -> None:
        self._llm = llm

    def run(self, research: ResearchResults) -> ResearchSummary:
        logger.info("Agent 2 Summarization started")
        try:
            source_data = [source.model_dump(mode="json") for source in research.sources]
            summary = self._llm.create_structured(
                "You are a careful research summarizer. Use only the supplied search results. "
                "Do not add facts from memory. Consolidate duplicate information. For each key "
                "finding, include one or more source_ids that directly support it. Return concise, "
                "clear prose.",
                f"Topic: {research.topic}\nSearch results:\n{json.dumps(source_data)}",
                ResearchSummary,
            )
            valid_ids = {source.source_id for source in research.sources}
            if any(not set(item.source_ids).issubset(valid_ids) for item in summary.key_findings):
                raise ValueError("The summary cited an unknown source.")
            logger.info("Agent 2 Summarization completed")
            return summary
        except Exception:
            logger.exception("Agent 2 Summarization failed")
            raise
