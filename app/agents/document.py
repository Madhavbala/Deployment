import json
import logging

from app.schemas import ResearchReport, ResearchResults, ResearchSummary, SourceReference
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)


class DocumentCreationAgent:
    def __init__(self, llm: GroqClient) -> None:
        self._llm = llm

    def run(self, summary: ResearchSummary, research: ResearchResults) -> ResearchReport:
        logger.info("Agent 3 Document Creation started")
        try:
            report = self._llm.create_structured(
                "You write professional, balanced research reports. Use only the supplied summary "
                "and search sources; do not invent facts, dates, statistics, or references. Every "
                "factual text block and key finding must include source_ids from the supplied "
                "sources. Keep the requested topic in focus. Return a complete report with title, "
                "executive_summary, introduction, sections (heading and body), key_findings, "
                "conclusion, and references.",
                "Topic: "
                + research.topic
                + "\nSummary:\n"
                + json.dumps(summary.model_dump(mode="json"))
                + "\nAvailable sources:\n"
                + json.dumps([source.model_dump(mode="json") for source in research.sources]),
                ResearchReport,
            )
            valid_ids = {source.source_id for source in research.sources}
            self._validate_report_sources(report, valid_ids)
            report.references = [
                SourceReference(
                    source_id=source.source_id,
                    title=source.title,
                    url=source.url,
                )
                for source in research.sources
            ]
            logger.info("Agent 3 Document Creation completed")
            return report
        except Exception:
            logger.exception("Agent 3 Document Creation failed")
            raise

    @staticmethod
    def _validate_report_sources(report: ResearchReport, valid_ids: set[str]) -> None:
        cited_ids = set(report.executive_summary.source_ids + report.introduction.source_ids + report.conclusion.source_ids)
        cited_ids.update(source_id for section in report.sections for source_id in section.body.source_ids)
        cited_ids.update(source_id for finding in report.key_findings for source_id in finding.source_ids)
        if not cited_ids or not cited_ids.issubset(valid_ids):
            raise ValueError("The report contains missing or unknown source citations.")
