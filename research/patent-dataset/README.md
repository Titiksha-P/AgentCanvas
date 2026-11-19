# Patent evaluation research dataset v0.2.0

This file contains 15 synthetic, hand-authored fixtures in `patent_cases.json`.
Each record includes a source claim, candidate text, explicit annotation metadata,
and one or more expected issue codes. The labels are engineering test oracles,
not legal determinations and not annotations by patent attorneys.

## Coverage
- Claim-limitation omission
- Unsupported technical additions
- Citation identifier membership mismatch
- Invalid claim dependency reference
- Missing antecedent basis

## Dataset protocol
The current set is a smoke-test and regression corpus. It is not a representative
sample of patent documents. Before research claims are made, build a separate
expert-reviewed corpus with source provenance, jurisdiction, technology domain,
claim-level spans, severity, adjudicated labels, annotator identity, and split
membership. Keep a held-out test set untouched during rule and prompt tuning.
Do not put confidential patent applications or privileged legal material into
external LLM services without authorization.

## Split policy
No train/dev/test split is declared for these 15 fixtures because they are too
small and synthetic. Do not use them to train a model or report generalization.
