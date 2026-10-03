from pathlib import Path
from unittest.mock import Mock

import pytest

from app.agents.document import DocumentCreationAgent
from app.agents.review import DocumentReviewAgent
from app.config import Settings
from app.schemas import CitedText, ResearchFinding, ResearchReport, ResearchResults, ResearchSummary, ReviewResult, SearchResult, SourceReference
from app.services.groq_client import GroqClient, LLMServiceError
from app.services.web_search import SearchServiceError, WebSearchService


@pytest.mark.parametrize(
    "factory, key_name, key_value",
    [
        (WebSearchService, "search_api_key", "your_tavily_api_key"),
        (GroqClient, "groq_api_key", "your_groq_api_key"),
    ],
)
def test_placeholder_api_keys_are_rejected_with_clear_error(factory, key_name, key_value):
    settings = Settings(
        groq_api_key="your_groq_api_key",
        groq_model="llama-3.3-70b-versatile",
        search_api_key="your_tavily_api_key",
        output_dir=Path("output"),
        groq_timeout_seconds=60,
        search_timeout_seconds=20,
    )
    settings_dict = settings.__dict__.copy()
    settings_dict[key_name] = key_value
    settings = Settings(**settings_dict)

    with pytest.raises((SearchServiceError, LLMServiceError), match="real|configured|placeholder|your_"):
        factory(settings)


def test_groq_requests_explicitly_mention_json_for_structured_output():
    settings = Settings(
        groq_api_key="gsk_valid_key",
        groq_model="openai/gpt-oss-120b",
        search_api_key="tvly_valid_key",
        output_dir=Path("output"),
        groq_timeout_seconds=60,
        search_timeout_seconds=20,
    )

    mock_client = Mock()
    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(content='{"status": "ok"}'))]
    mock_client.chat.completions.create.return_value = mock_completion

    client = GroqClient.__new__(GroqClient)
    client._model = settings.groq_model
    client._client = mock_client

    client.create_structured(
        "Write a report.",
        "Make a summary.",
        type("DummyModel", (), {"model_validate": staticmethod(lambda data: data), "model_json_schema": staticmethod(lambda: {"type": "object", "properties": {"status": {"type": "string"}}})}),
    )

    payload = mock_client.chat.completions.create.call_args.kwargs
    assert payload["response_format"] == {"type": "json_object"}
    messages = payload["messages"]
    assert any("json" in str(message["content"]).lower() for message in messages)
    assert any("schema" in str(message["content"]).lower() for message in messages)


def test_report_references_are_cast_to_source_reference_objects():
    report = ResearchReport(
        title="Test title",
        executive_summary=CitedText(text="Summary", source_ids=["S1"]),
        introduction=CitedText(text="Intro", source_ids=["S1"]),
        sections=[{"heading": "Section 1", "body": {"text": "Text", "source_ids": ["S1"]}}],
        key_findings=[ResearchFinding(claim="Finding 1", source_ids=["S1"])],
        conclusion=CitedText(text="Conclusion", source_ids=["S1"]),
        references=[],
    )
    summary = ResearchSummary(
        executive_summary="Summary",
        overview="Overview",
        key_findings=[ResearchFinding(claim="Finding 1", source_ids=["S1"])],
    )
    research = ResearchResults(
        topic="Climate resilience",
        sources=[SearchResult(source_id="S1", title="Source 1", url="https://example.com/a", snippet="snippet")],
    )

    llm = Mock()
    llm.create_structured.side_effect = [report, ReviewResult(report=report, review_notes=[])]

    result = DocumentCreationAgent(llm).run(summary, research)
    assert all(isinstance(item, SourceReference) for item in result.references)

    reviewed = DocumentReviewAgent(llm).run(result, research.sources)
    assert all(isinstance(item, SourceReference) for item in reviewed.report.references)
