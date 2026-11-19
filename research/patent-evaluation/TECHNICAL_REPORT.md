# AgentCanvas Patent Output Evaluation — Technical Report

**Status:** research prototype, version 0.2.0  
**Dataset:** 20 synthetic fixtures  
**Scope:** observable text-level failure signals only

## Objective
Test whether an AI-generated patent-style output preserves configured source-claim
limitations, avoids configured unsupported technical additions, uses citation IDs
present in a supplied evidence set, avoids configured invalid dependency references,
and introduces configured elements before definite references.

## Architecture
AgentCanvas owns the patent-domain evaluator. Cognisynth contributes an architectural
pattern: treat generated output as untrusted, validate it against explicit invariants,
and fail closed when validation cannot complete. Cognisynth's existing UI blueprint
validator is not imported as patent logic; UI state reachability rules are not patent
claim rules. A separate domain adapter is the appropriate boundary.

## Baselines
1. **Deterministic rules:** explicit configured phrases and regular-expression checks.
2. **Semantic heuristic:** lexical overlap proxy, polarity-marker difference, and exact
   configured evidence-quote presence.
3. **Optional LLM judge:** OpenAI Responses API comparator; advisory, non-deterministic,
   and disabled unless explicitly requested and an API key is configured.
4. **Hybrid:** combines deterministic findings with heuristic findings; optional LLM
   findings are appended and never suppress deterministic violations.

## Metrics
Micro precision, recall, F1, false-positive/false-negative counts, a false-positive
proxy, duration, and per-case findings are recorded. Metrics are computed against
synthetic expected issue codes. The proxy is not a conventional population false-positive rate because
the fixture set does not enumerate all true-negative opportunities.

## Limitations
- Fifteen synthetic cases are not representative of patent drafting or prosecution.
- Lexical overlap does not establish semantic equivalence.
- Citation ID membership does not establish that a source supports a proposition.
- No external prior-art search, claim construction, novelty, inventive-step,
  infringement, validity, patentability, or legal-sufficiency analysis is performed.
- The optional LLM judge can hallucinate, vary between runs, and require expert review.
- No expert-labelled corpus or inter-annotator agreement study exists yet.

## Reproduction
From the repository root:
```bash
python -m pip install -r backend/requirements.txt
python -m unittest discover -s backend/tests -v
cd backend && uvicorn app:app --reload --port 8080
```
Then call `GET /api/patent-evaluate` and `POST /api/patent-experiments`.
The LLM baseline requires `OPENAI_API_KEY`; all other baselines are offline.

## Research next gate
Acquire permissioned, de-identified patent text; recruit qualified annotators;
define annotation guidelines; measure agreement; freeze held-out splits; and compare
the baselines on that corpus before claiming external validity or deployment readiness.
