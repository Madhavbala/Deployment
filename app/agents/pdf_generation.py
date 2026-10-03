import logging
from pathlib import Path

from app.schemas import ResearchReport
from app.services.pdf import generate_report_pdf

logger = logging.getLogger(__name__)


class PDFGenerationAgent:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def run(self, report: ResearchReport) -> str:
        logger.info("Agent 5 PDF Generation started")
        try:
            filename = generate_report_pdf(report, self._output_dir)
            logger.info("Agent 5 PDF Generation completed")
            return filename
        except Exception:
            logger.exception("Agent 5 PDF Generation failed")
            raise
