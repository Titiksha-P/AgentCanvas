const state = {
  agent: null,
  scenarios: JSON.parse(localStorage.getItem("agentcanvas_scenarios") || "[]"),
  lastEvaluation: null
};

const $ = id => document.getElementById(id);

function buildAgentFromForm() {
  return {
    name: $("agent-name").value.trim(),
    purpose: $("agent-purpose").value.trim(),
    systemPrompt: $("system-prompt").value.trim(),
    tools: $("tools").value.split(",").map(x => x.trim()).filter(Boolean),
    permissions: $("permissions").value.trim(),
    businessRules: $("business-rules").value.trim(),
    samplePrompt: $("sample-prompt").value.trim(),
    memorySettings: $("memory-settings").value
  };
}

function averageBehaviour(scores) {
  const values = [
    scores.empathy_score,
    scores.trust_score,
    scores.confidence_score,
    scores.consistency_score,
    scores.clarity_score,
    scores.user_satisfaction_score
  ];
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function renderBehaviour(behaviour) {
  const labels = {
    empathy_score: "Empathy",
    trust_score: "Trust",
    confidence_score: "Confidence",
    consistency_score: "Consistency",
    clarity_score: "Clarity",
    user_satisfaction_score: "User satisfaction"
  };

  const scores = behaviour;
  $("behaviour-cards").innerHTML = Object.entries(labels)
    .map(([key, label]) => `<article class="score-card"><strong>${scores[key]}</strong><span>${label}</span></article>`)
    .join("");

  const rationale = scores.rationale || {};
  $("behaviour-explanations").innerHTML = Object.entries(rationale)
    .map(([dimension, text]) => `<div class="explanation"><strong>${dimension.replaceAll("_", " ")}</strong>: ${text}</div>`)
    .join("");
}

function pickNumber(value, fallback = 0) {
  if (typeof value === "number") return value;
  if (value && typeof value === "object") {
    for (const key of ["score", "risk_score", "compliance_score", "value"]) {
      if (typeof value[key] === "number") return value[key];
    }
  }
  return fallback;
}

function pickBoolean(value, keys = ["detected", "is_detected", "found"]) {
  if (typeof value === "boolean") return value;
  if (value && typeof value === "object") {
    for (const key of keys) if (typeof value[key] === "boolean") return value[key];
  }
  return false;
}

function renderDashboard(evaluation) {
  const security = evaluation.security || {};
  const behaviourScore = averageBehaviour(evaluation.behaviour);
  const riskScore = pickNumber(security.risk, 100);
  const complianceScore = pickNumber(security.compliance, 0);
  const securityScore = Math.max(0, 100 - riskScore);

  $("readiness-score").textContent = evaluation.readiness_score;
  $("behaviour-score").textContent = behaviourScore;
  $("performance-score").textContent = evaluation.performance_score;
  $("security-score").textContent = securityScore;
  $("compliance-score").textContent = complianceScore;

  const injectionDetected = pickBoolean(security.prompt_injection);
  const sensitiveDetected = pickBoolean(security.sensitive_data);
  $("injection-result").textContent = injectionDetected ? "Detected" : "Not detected";
  $("sensitive-result").textContent = sensitiveDetected ? "Potential exposure detected" : "No exposure detected";
  $("deployment-status").textContent = evaluation.deployment_status;

  const recommendations = [];
  if (injectionDetected) recommendations.push("Strengthen system instructions and expand adversarial prompt tests.");
  if (sensitiveDetected) recommendations.push("Restrict sensitive fields and add output masking before deployment.");
  if (complianceScore < 75) recommendations.push("Review business rules and require explicit approval for high-impact actions.");
  if (evaluation.behaviour.empathy_score < 75) recommendations.push("Improve acknowledgement and supportive language for difficult user situations.");
  if (evaluation.behaviour.trust_score < 75) recommendations.push("Make uncertainty, limitations and escalation paths more transparent.");
  if (evaluation.performance_score < 75) recommendations.push("Improve task completion quality, consistency and response latency.");
  if (!recommendations.length) recommendations.push("The agent performed well in this scenario. Continue regression testing after every prompt, model or tool change.");
  $("recommendation-list").innerHTML = recommendations.map(item => `<li>${item}</li>`).join("");
}

function securitySummary(evaluation) {
  const security = evaluation.security || {};
  const risk = security.risk || {};
  const severity = risk.severity || risk.risk_level || "unknown";
  const score = pickNumber(risk, 0);
  const injection = pickBoolean(security.prompt_injection);
  const sensitive = pickBoolean(security.sensitive_data);
  return `Risk: ${severity} (${score}/100). Prompt injection: ${injection ? "detected" : "not detected"}. Sensitive-data risk: ${sensitive ? "detected" : "not detected"}. Latency: ${evaluation.latency_ms} ms.`;
}

function showError(message) {
  $("agent-output").textContent = "No result generated.";
  $("security-result").textContent = message;
  const badge = $("safety-badge");
  badge.textContent = "Evaluation failed";
  badge.className = "badge unsafe";
}

$("agent-form").addEventListener("submit", event => {
  event.preventDefault();
  state.agent = buildAgentFromForm();
  localStorage.setItem("agentcanvas_agent", JSON.stringify(state.agent));
  $("agent-saved").textContent = `${state.agent.name} has been saved and is ready for testing.`;
  $("agent-saved").classList.remove("hidden");
});

$("run-test").addEventListener("click", async () => {
  state.agent = state.agent || buildAgentFromForm();
  const userPrompt = $("test-prompt").value.trim();
  const scenarioName = $("scenario-name").value.trim() || "Untitled scenario";
  if (!userPrompt) return;

  $("run-test").disabled = true;
  $("run-test").textContent = "Running…";
  $("agent-output").textContent = "Generating a live AI response…";
  $("security-result").textContent = "Running live AI, behavioural and security evaluation…";

  try {
    const evaluation = await window.AgentCanvasAPI.evaluateAgent({
      agent: state.agent,
      scenarioName,
      userPrompt
    });

    state.lastEvaluation = evaluation;
    $("agent-output").textContent = evaluation.agent_response;
    $("security-result").textContent = securitySummary(evaluation);

    const unsafe = evaluation.deployment_status === "Blocked" || evaluation.deployment_status === "Needs Review";
    const badge = $("safety-badge");
    badge.textContent = unsafe ? evaluation.deployment_status : "Safe for this scenario";
    badge.className = `badge ${unsafe ? "unsafe" : "safe"}`;

    renderBehaviour(evaluation.behaviour);
    renderDashboard(evaluation);
  } catch (error) {
    showError(error.message || "Evaluation failed. Confirm that both backends are running and correctly configured.");
  } finally {
    $("run-test").disabled = false;
    $("run-test").textContent = "Run Test";
  }
});

$("save-scenario").addEventListener("click", () => {
  const scenario = {
    id: Date.now(),
    name: $("scenario-name").value.trim() || "Untitled scenario",
    prompt: $("test-prompt").value.trim(),
    evaluation: state.lastEvaluation,
    createdAt: new Date().toISOString()
  };
  state.scenarios.push(scenario);
  localStorage.setItem("agentcanvas_scenarios", JSON.stringify(state.scenarios));
  $("scenario-notice").textContent = `Saved “${scenario.name}” locally with its latest evaluation.`;
  $("scenario-notice").classList.remove("hidden");
});

(function initialise() {
  const savedAgent = JSON.parse(localStorage.getItem("agentcanvas_agent") || "null");
  if (savedAgent) {
    state.agent = savedAgent;
    $("agent-name").value = savedAgent.name || "";
    $("agent-purpose").value = savedAgent.purpose || "";
    $("system-prompt").value = savedAgent.systemPrompt || "";
    $("tools").value = (savedAgent.tools || []).join(", ");
    $("permissions").value = savedAgent.permissions || "";
    $("business-rules").value = savedAgent.businessRules || "";
    $("sample-prompt").value = savedAgent.samplePrompt || "";
    $("memory-settings").value = savedAgent.memorySettings || "Session memory only";
  }

  $("behaviour-cards").innerHTML = '<article class="score-card"><strong>—</strong><span>Run a live test</span></article>';
  $("behaviour-explanations").innerHTML = '<div class="explanation">Behaviour scores appear only after the live model evaluates a real response.</div>';
})();
