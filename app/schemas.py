from pydantic import BaseModel, Field, HttpUrl


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)


class SearchResult(BaseModel):
    source_id: str
    title: str
    url: HttpUrl
    snippet: str


class ResearchResults(BaseModel):
    topic: str
    sources: list[SearchResult]


class CitedText(BaseModel):
    text: str
    source_ids: list[str] = Field(default_factory=list)


class ResearchFinding(BaseModel):
    claim: str
    source_ids: list[str] = Field(min_length=1)


class ResearchSummary(BaseModel):
    executive_summary: str
    overview: str
    key_findings: list[ResearchFinding]


class ReportSection(BaseModel):
    heading: str
    body: CitedText


class SourceReference(BaseModel):
    source_id: str
    title: str
    url: HttpUrl


class ResearchReport(BaseModel):
    title: str
    executive_summary: CitedText
    introduction: CitedText
    sections: list[ReportSection]
    key_findings: list[ResearchFinding]
    conclusion: CitedText
    references: list[SourceReference] = Field(default_factory=list)


class ReviewResult(BaseModel):
    report: ResearchReport
    review_notes: list[str] = Field(default_factory=list)


class ResearchReportResponse(BaseModel):
    status: str
    topic: str
    report: ResearchReport
    review_notes: list[str]
    pdf_filename: str
    pdf_download_url: str
