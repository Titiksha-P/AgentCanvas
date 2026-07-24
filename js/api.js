const EVALUATION_API_URL = window.AGENTCANVAS_API_URL || "http://localhost:8080/api/evaluate";
const HEALTH_API_URL = window.AGENTCANVAS_HEALTH_URL || "http://localhost:8080/api/health";

async function parseJsonResponse(response) {
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Backend returned ${response.status} with a non-JSON response.`);
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.message || `Backend returned ${response.status}`;
    throw new Error(detail);
  }

  return payload;
}

async function evaluateAgent({ agent, scenarioName, userPrompt }) {
  const response = await fetch(EVALUATION_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agent: {
        name: agent.name,
        purpose: agent.purpose,
        system_prompt: agent.systemPrompt,
        tools: agent.tools,
        permissions: agent.permissions,
        business_rules: agent.businessRules,
        memory_settings: agent.memorySettings
      },
      scenario_name: scenarioName,
      user_prompt: userPrompt
    })
  });

  return parseJsonResponse(response);
}

async function checkBackendHealth() {
  const response = await fetch(HEALTH_API_URL);
  return parseJsonResponse(response);
}

window.AgentCanvasAPI = {
  EVALUATION_API_URL,
  HEALTH_API_URL,
  evaluateAgent,
  checkBackendHealth
};
