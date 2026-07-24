const SECURITY_API_URL = "http://localhost:8000/api/v1/security/analyze";

async function runSecurityAnalysis(prompt) {
  try {
    const response = await fetch(SECURITY_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });

    if (!response.ok) {
      throw new Error(`Security engine returned ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return {
      offline: true,
      error: error.message,
      risk: { risk_score: 55, severity: "medium" },
      policy: { allowed: false, reason: "Live security engine unavailable; using demo fallback." },
      sensitive_data: { detected: /credit card|password|api key|customer data/i.test(prompt) },
      compliance: { score: 62 },
      prompt_injection: { detected: /ignore all|ignore previous|reveal.*prompt|jailbreak/i.test(prompt) },
      threat_simulation: { result: "Potential manipulation attempt detected." },
      security_report: "Demo result generated because the local FastAPI service could not be reached."
    };
  }
}

window.AgentCanvasAPI = { runSecurityAnalysis, SECURITY_API_URL };
