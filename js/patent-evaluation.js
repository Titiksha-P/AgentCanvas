const runButton = document.getElementById("run-benchmark");
const statusNode = document.getElementById("run-status");
const errorNode = document.getElementById("benchmark-error");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function renderCase(item) {
  const findings = item.findings.length
    ? item.findings.map(f => `<div class="finding"><strong>${escapeHtml(f.code)}</strong><br>${escapeHtml(f.message)}</div>`).join("")
    : '<div class="finding">No configured rule fired for this case.</div>';
  const expected = item.expected_issue_codes.map(escapeHtml).join(", ");
  return `
    <article class="benchmark-case">
      <div class="case-head">
        <div><div class="case-id">${escapeHtml(item.id)}</div><div class="case-title">${escapeHtml(item.title)}</div><div class="case-category">${escapeHtml(item.category)}</div></div>
        <span class="case-status ${item.matched_expected_failures ? "" : "missed"}">${item.matched_expected_failures ? "Expected issues detected" : "Detection gap"}</span>
      </div>
      <div class="case-copy"><strong>Source claim</strong><br>${escapeHtml(item.source_claim)}</div>
      <div class="case-copy"><strong>Candidate output</strong><br>${escapeHtml(item.candidate_output)}</div>
      <div class="case-copy"><strong>Expected issue codes</strong><br>${expected || "None"}</div>
      <div>${findings}</div>
      <div class="case-category">Recall: ${Math.round(item.recall * 100)}% · Case score: ${item.score}/100</div>
    </article>`;
}

async function runBenchmark() {
  runButton.disabled = true;
  runButton.textContent = "Running…";
  statusNode.textContent = "Evaluating the synthetic regression corpus";
  errorNode.classList.add("hidden");
  try {
    const configuredApi = window.AGENTCANVAS_PATENT_API_URL || window.AGENTCANVAS_API_URL;
    const localApi = ["localhost", "127.0.0.1"].includes(window.location.hostname)
      ? "http://localhost:8080"
      : "";
    const apiBase = (configuredApi || localApi).replace(/\/+$/, "");
    const response = await fetch(`${apiBase}/api/patent-evaluate`);
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || `Backend returned ${response.status}`);
    document.getElementById("metric-detection").textContent = `${report.detection_rate_percent}%`;
    document.getElementById("metric-precision").textContent = `${Math.round(report.precision * 100)}%`;
    document.getElementById("metric-recall").textContent = `${Math.round(report.recall * 100)}%`;
    document.getElementById("metric-cases").textContent = `${report.cases_with_all_expected_failures_detected}/${report.case_count}`;
    document.getElementById("metric-fp").textContent = report.false_positives;
    document.getElementById("metric-fn").textContent = report.false_negatives;
    document.getElementById("metric-mode").textContent = report.evaluation_mode.replaceAll("_", " ");
    document.getElementById("case-list").innerHTML = report.results.map(renderCase).join("");
    document.getElementById("summary").classList.remove("hidden");
    document.getElementById("case-results").classList.remove("hidden");
    statusNode.textContent = `Completed · ${report.case_count} cases · ${report.detected_expected_issues}/${report.expected_issue_count} expected issues detected`;
  } catch (error) {
    errorNode.textContent = `${error.message}. Start the AgentCanvas backend and retry.`;
    errorNode.classList.remove("hidden");
    statusNode.textContent = "Run failed";
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run patent benchmark";
  }
}

runButton.addEventListener("click", runBenchmark);
