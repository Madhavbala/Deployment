# Fieldnotes Research Report Generator

A small FastAPI application that runs five sequential agents: live web research with Tavily, source-grounded summarization with Groq, report drafting, report review, and PDF generation with ReportLab. The browser interface and JSON API both return the final report and a PDF download URL.

## Requirements

- Python 3.10 or newer
- A Groq API key and a Tavily Search API key

## Install

From the project directory, create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies and create your local environment file:

```powershell
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `.env` and set `GROQ_API_KEY` and `SEARCH_API_KEY`. Get credentials from [Groq](https://console.groq.com/keys) and [Tavily](https://app.tavily.com/). Set `GROQ_MODEL` to a model enabled for your Groq account (for example, `openai/gpt-oss-120b` if it is available on your account). Keys are loaded from `.env` and are never written to application logs.

## Run

```powershell
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the research form or <http://127.0.0.1:8000/docs> for the interactive API documentation. Generated PDFs are saved in `output/` by default; set `OUTPUT_DIR` to change that location.

## API

Create a report:

```powershell
$body = @{ topic = "How are cities adapting to extreme heat?" } | ConvertTo-Json
$result = Invoke-RestMethod -Uri http://127.0.0.1:8000/research-report -Method Post -ContentType "application/json" -Body $body
$result | ConvertTo-Json -Depth 12
```

The JSON response contains `status`, the reviewed `report`, `review_notes`, `pdf_filename`, and `pdf_download_url`. Visit that download URL in a browser, or download it from PowerShell:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000$($result.pdf_download_url)" -OutFile $result.pdf_filename
```

The report endpoint runs synchronously and returns only after all five agents finish. Search results and citations come from the Tavily response; if search yields no usable sources, report generation stops instead of inventing references.

## Run with Docker on Windows

This project uses one container for the FastAPI app and its bundled static frontend. It has no database or migration step. Groq and Tavily remain external services, so the container needs outbound network access and valid API keys. Generated PDFs are stored in a named Docker volume and remain available after the container is removed.

Open the project folder in VS Code and use a PowerShell terminal. Create the local environment file from the safe template, then edit it with your API keys:

```powershell
Copy-Item .env.example .env
notepad .env
```

Validate the Compose file, build the image, and start the app:

```powershell
docker compose config --quiet
docker compose up --build --detach
```

Open <http://localhost:8000> for the app, <http://localhost:8000/docs> for API docs, and <http://localhost:8000/dashboard> for metrics. The container health check calls `/health`; check its state with:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-WebRequest http://localhost:8000/ -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest http://localhost:8000/dashboard -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest http://localhost:8000/metrics -UseBasicParsing | Select-Object StatusCode
```

To exercise the full workflow, which sends requests to Tavily and Groq and uses their account quotas:

```powershell
$body = @{ topic = "How are cities adapting to extreme heat?" } | ConvertTo-Json
$result = Invoke-RestMethod -Uri http://localhost:8000/research-report -Method Post -ContentType "application/json" -Body $body
$result.pdf_download_url
Invoke-WebRequest -Uri "http://localhost:8000$($result.pdf_download_url)" -OutFile $result.pdf_filename
```

View logs, stop the app, and start it again with:

```powershell
docker compose logs --follow app
docker compose stop
docker compose start
```

To rebuild and recreate the running container after changing the image:

```powershell
docker compose up --build --detach
```

To remove the container and network while keeping the `fieldnotes-reports` volume and its PDFs, run:

```powershell
docker compose down
```

Troubleshooting:

- If Docker commands cannot connect to the engine, start Docker Desktop and check `docker info`.
- If port 8000 is already in use, set `$env:FIELDNOTES_PORT = "8001"` in PowerShell before `docker compose up --build --detach`, then open `http://localhost:8001`.
- If Compose reports that `.env` is missing, copy `.env.example` to `.env` and set valid `GROQ_API_KEY` and `SEARCH_API_KEY` values. Do not put `.env` values in the Dockerfile or image.
- If `/health` works but report generation fails, inspect `docker compose logs app`; check outbound network access, provider quota, and that `GROQ_MODEL` is enabled for your Groq account.

## Tests

Run the offline test suite with:

```powershell
python -m pytest
```

The tests mock external API calls while checking sequential agent handoffs, source handling, PDF output, and download validation.

## Continuous Integration

The GitHub Actions workflow at `.github/workflows/ci.yml` runs on pushes to `main` and pull requests targeting `main`. It installs the development requirements, checks Python syntax, runs the existing offline tests, validates the Compose configuration, and builds the Docker image. It does not call Groq or Tavily, publish the image, or require repository secrets; Compose validation uses a temporary `.env` copied from the placeholder-only `.env.example`.

After this workflow is committed and pushed to GitHub, open the repository's **Actions** tab and select **CI** to see each run and its test/build logs. On a pull request, the **Tests, Compose validation, and Docker build** check appears in the PR's checks section. This workspace currently has no Git remote configured, so the workflow must be committed and pushed to the intended GitHub repository before a hosted run can appear.
