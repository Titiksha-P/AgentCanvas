function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function scoreBehaviour(responseText, userPrompt) {
  const response = (responseText || "").trim();
  const prompt = (userPrompt || "").trim();
  const lower = response.toLowerCase();

  const empathySignals = ["understand", "sorry", "frustrat", "help", "concern"];
  const transparencySignals = ["cannot", "not able", "uncertain", "human approval", "policy"];
  const claritySignals = ["because", "next", "step", "recommend", "please"];

  const empathy = 58 + empathySignals.filter(s => lower.includes(s)).length * 8;
  const trust = 55 + transparencySignals.filter(s => lower.includes(s)).length * 9 - (/guarantee|definitely|100%/i.test(response) ? 12 : 0);
  const confidence = 68 + (response.length > 35 ? 8 : -8) - (/maybe|probably|i think/i.test(response) ? 6 : 0);
  const consistency = 74 + (response.length > 10 ? 6 : -12);
  const clarity = 62 + claritySignals.filter(s => lower.includes(s)).length * 6 + (response.length < 420 ? 8 : -6);
  const satisfaction = (empathy + trust + clarity) / 3 + (prompt.length > 0 ? 3 : 0);

  const scores = {
    empathy_score: clamp(empathy),
    trust_score: clamp(trust),
    confidence_score: clamp(confidence),
    consistency_score: clamp(consistency),
    clarity_score: clamp(clarity),
    user_satisfaction_score: clamp(satisfaction)
  };

  const average = clamp(Object.values(scores).reduce((a, b) => a + b, 0) / 6);

  const explanations = [
    `Empathy: ${scores.empathy_score >= 75 ? "Good" : "Needs improvement"}. ${scores.empathy_score >= 75 ? "The response recognises the user's situation and offers support." : "The response could acknowledge the user's feelings or concern more clearly."}`,
    `Trust: ${scores.trust_score >= 75 ? "Good" : "Medium"}. ${scores.trust_score >= 75 ? "The agent communicates limits and follows clear boundaries." : "The agent should explain limits, uncertainty and approval requirements more openly."}`,
    `Clarity: ${scores.clarity_score >= 80 ? "Excellent" : "Fair"}. ${scores.clarity_score >= 80 ? "The answer is direct and easy to act on." : "The answer could be shorter, more structured and more specific."}`
  ];

  return { scores, average, explanations };
}

window.BehaviourEngine = { scoreBehaviour };
