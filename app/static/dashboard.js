async function loadMetrics() {
  const response = await fetch('/metrics');
  if (!response.ok) {
    throw new Error('Metrics are unavailable right now.');
  }

  const text = await response.text();
  const metrics = {
    success: 0,
    error: 0,
    successSum: 0,
    errorSum: 0,
    successCount: 0,
    errorCount: 0,
  };

  const lines = text.split('\n');
  for (const line of lines) {
    if (!line.startsWith('research_report_flow_total')) {
      continue;
    }
    const match = line.match(/status="([^"]+)"\s+(\d+(?:\.\d+)?)/);
    if (!match) continue;
    const [, status, value] = match;
    const numeric = Number(value);
    if (status === 'success') metrics.success = numeric;
    if (status === 'error') metrics.error = numeric;
  }

  for (const line of lines) {
    if (!line.startsWith('research_report_flow_duration_seconds_sum')) {
      continue;
    }
    const match = line.match(/status="([^"]+)"\s+(\d+(?:\.\d+)?)/);
    if (!match) continue;
    const [, status, value] = match;
    const numeric = Number(value);
    if (status === 'success') metrics.successSum = numeric;
    if (status === 'error') metrics.errorSum = numeric;
  }

  for (const line of lines) {
    if (!line.startsWith('research_report_flow_duration_seconds_count')) {
      continue;
    }
    const match = line.match(/status="([^"]+)"\s+(\d+(?:\.\d+)?)/);
    if (!match) continue;
    const [, status, value] = match;
    const numeric = Number(value);
    if (status === 'success') metrics.successCount = numeric;
    if (status === 'error') metrics.errorCount = numeric;
  }

  const successAvg = metrics.successCount > 0 ? metrics.successSum / metrics.successCount : 0;
  const errorAvg = metrics.errorCount > 0 ? metrics.errorSum / metrics.errorCount : 0;

  document.getElementById('success-count').textContent = metrics.success.toString();
  document.getElementById('error-count').textContent = metrics.error.toString();
  document.getElementById('avg-duration').textContent = `${successAvg.toFixed(2)}s`;

  document.getElementById('success-row').textContent = `${metrics.success}`;
  document.getElementById('error-row').textContent = `${metrics.error}`;
  document.getElementById('avg-row').textContent = `${successAvg.toFixed(2)}s`;

  const statusPill = document.getElementById('status-pill');
  statusPill.textContent = metrics.error > 0 ? 'Needs attention' : 'Healthy';
  statusPill.style.background = metrics.error > 0 ? '#fff1dd' : '#eef5ee';
  statusPill.style.color = metrics.error > 0 ? '#a5640a' : '#1d6f64';

  if (errorAvg > 0) {
    console.info(`Average error flow duration: ${errorAvg.toFixed(2)}s`);
  }
}

loadMetrics().catch((error) => {
  const statusPill = document.getElementById('status-pill');
  statusPill.textContent = 'Unavailable';
  statusPill.style.background = '#fde6e6';
  statusPill.style.color = '#8b2f2f';
  console.error(error);
});
