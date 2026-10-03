import logging
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

from app.agents.document import DocumentCreationAgent
from app.agents.pdf_generation import PDFGenerationAgent
from app.agents.research import ResearchAgent
from app.agents.review import DocumentReviewAgent
from app.agents.summarization import SummarizationAgent
from app.config import get_settings
from app.schemas import ResearchReportResponse, ResearchRequest
from app.services.groq_client import GroqClient, LLMServiceError
from app.services.pdf import PDFServiceError
from app.services.web_search import SearchServiceError, WebSearchService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
APP_DIR = Path(__file__).resolve().parent

RESEARCH_REPORT_TOTAL = Counter(
    "research_report_flow_total",
    "Total number of completed research-report workflows by result.",
    labelnames=("status",),
)
RESEARCH_REPORT_LATENCY = Histogram(
    "research_report_flow_duration_seconds",
    "Time spent completing one research-report workflow.",
    labelnames=("status",),
)

app = FastAPI(
    title="Research Report Generator",
    description="Sequential web research and cited PDF report generation.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

instrumentator = Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/metrics"],
    should_ignore_untemplated=True,
)
instrumentator.instrument(app)
instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "dashboard.html")


@app.post("/research-report", response_model=ResearchReportResponse, tags=["research"])
def create_research_report(payload: ResearchRequest) -> ResearchReportResponse:
    settings = get_settings()
    status = "success"
    started_at = time.perf_counter()
    try:
        search_service = WebSearchService(settings)
        research = ResearchAgent(search_service).run(payload.topic.strip())
        llm = GroqClient(settings)
        summary = SummarizationAgent(llm).run(research)
        draft = DocumentCreationAgent(llm).run(summary, research)
        review = DocumentReviewAgent(llm).run(draft, research.sources)
        filename = PDFGenerationAgent(settings.output_dir).run(review.report)
    except SearchServiceError as exc:
        status = "error"
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMServiceError as exc:
        status = "error"
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except PDFServiceError as exc:
        status = "error"
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        status = "error"
        logger.exception("Research report workflow failed")
        raise HTTPException(
            status_code=502,
            detail="A report-generation step failed. See server logs for details.",
        ) from exc
    finally:
        elapsed = time.perf_counter() - started_at
        RESEARCH_REPORT_TOTAL.labels(status=status).inc()
        RESEARCH_REPORT_LATENCY.labels(status=status).observe(elapsed)

    return ResearchReportResponse(
        status="completed",
        topic=research.topic,
        report=review.report,
        review_notes=review.review_notes,
        pdf_filename=filename,
        pdf_download_url=f"/download/{filename}",
    )


@app.get("/download/{filename}", name="download_report", tags=["research"])
def download_report(filename: str) -> FileResponse:
    if not re.fullmatch(r"research-report-[a-f0-9]{12}\.pdf", filename):
        raise HTTPException(status_code=404, detail="Report not found.")

    output_dir = get_settings().output_dir.resolve()
    path = (output_dir / filename).resolve()
    if not path.is_relative_to(output_dir) or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path, media_type="application/pdf", filename=filename)
