import json
import logging

from app.schemas import ResearchReport, ReviewResult, SearchResult, SourceReference
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)


class DocumentReviewAgent:
    def __init__(self, llm: GroqClient) -> None:
        self._llm = llm

    def run(self, report: ResearchReport, sources: list[SearchResult]) -> ReviewResult:
        logger.info("Agent 4 Document Review started")
        try:
            reviewed = self._llm.create_structured(
                "You are a meticulous editor reviewing a research report against the provided "
                "source snippets. Check clarity, grammar, structure, completeness, consistency, "
                "unsupported claims, and missing citations. Revise the report to fix issues. "
                "Do not introduce facts or references not present in the source material. Use "
                "only the supplied source_ids for citations. Return the revised report and concise, "
                "actionable review_notes. If no material issues remain, return an empty notes list.",
                "Report:\n"
                + json.dumps(report.model_dump(mode="json"))
                + "\nSource material:\n"
                + json.dumps([source.model_dump(mode="json") for source in sources]),
                ReviewResult,
            )
            valid_ids = {source.source_id for source in sources}
            revised = reviewed.report
            cited_ids = set(
                revised.executive_summary.source_ids
                + revised.introduction.source_ids
                + revised.conclusion.source_ids
            )
            cited_ids.update(source_id for section in revised.sections for source_id in section.body.source_ids)
            cited_ids.update(source_id for finding in revised.key_findings for source_id in finding.source_ids)
            if not cited_ids or not cited_ids.issubset(valid_ids):
                raise ValueError("The reviewed report contains missing or unknown citations.")
            revised.references = [
                SourceReference(
                    source_id=source.source_id,
                    title=source.title,
                    url=source.url,
                )
                for source in sources
            ]
            logger.info("Agent 4 Document Review completed")
            return reviewed
        except Exception:
            logger.exception("Agent 4 Document Review failed")
            raise
