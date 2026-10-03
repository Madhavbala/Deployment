const form = document.querySelector('#research-form');
const topicInput = document.querySelector('#topic');
const submitButton = document.querySelector('#submit-button');
const statusBox = document.querySelector('#status');
const results = document.querySelector('#results');

function appendText(parent, tag, text, className = '') {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.append(element);
  return element;
}

function renderCitedText(parent, item, tag = 'p') {
  const paragraph = appendText(parent, tag, item.text);
  if (item.source_ids?.length) {
    const citations = document.createElement('span');
    citations.className = 'citation';
    citations.textContent = `  [${item.source_ids.join(', ')}]`;
    paragraph.append(citations);
  }
}

function renderReport(data) {
  const report = data.report;
  document.querySelector('#report-title').textContent = report.title;
  const content = document.querySelector('#report-content');
  content.replaceChildren();

  appendText(content, 'h3', 'Executive summary');
  renderCitedText(content, report.executive_summary);
  appendText(content, 'h3', 'Introduction');
  renderCitedText(content, report.introduction);

  for (const section of report.sections) {
    appendText(content, 'h3', section.heading, 'report-section-title');
    renderCitedText(content, section.body);
  }

  appendText(content, 'h3', 'Key findings', 'report-section-title');
  const findings = document.createElement('ul');
  findings.className = 'findings';
  for (const finding of report.key_findings) {
    const item = appendText(findings, 'li', finding.claim);
    const citations = document.createElement('span');
    citations.className = 'citation';
    citations.textContent = `  [${finding.source_ids.join(', ')}]`;
    item.append(citations);
  }
  content.append(findings);

  appendText(content, 'h3', 'Conclusion', 'report-section-title');
  renderCitedText(content, report.conclusion);

  const sourceList = document.querySelector('#source-list');
  sourceList.replaceChildren();
  for (const source of report.references) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = source.url;
    link.target = '_blank';
    link.rel = 'noreferrer';
    link.textContent = `[${source.source_id}] ${source.title}`;
    item.append(link);
    sourceList.append(item);
  }

  const notes = document.querySelector('#review-notes');
  notes.replaceChildren();
  if (data.review_notes.length) {
    appendText(notes, 'strong', 'Review notes');
    const list = document.createElement('ul');
    for (const note of data.review_notes) appendText(list, 'li', note);
    notes.append(list);
    notes.hidden = false;
  } else {
    notes.hidden = true;
  }

  document.querySelector('#download-link').href = data.pdf_download_url;
  results.hidden = false;
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (topic.length < 3) {
    topicInput.setCustomValidity('Enter at least 3 characters.');
    topicInput.reportValidity();
    return;
  }
  topicInput.setCustomValidity('');
  submitButton.disabled = true;
  statusBox.hidden = false;
  statusBox.className = 'status loading';
  statusBox.textContent = 'Searching sources, drafting, and reviewing your report…';
  results.hidden = true;

  try {
    const response = await fetch('/research-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The report could not be generated.');
    renderReport(data);
    statusBox.className = 'status';
    statusBox.textContent = 'Report ready. The PDF includes clickable source references.';
  } catch (error) {
    statusBox.className = 'status error';
    statusBox.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

topicInput.addEventListener('input', () => topicInput.setCustomValidity(''));
