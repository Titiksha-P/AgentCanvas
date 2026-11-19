# Annotation guidelines for the synthetic patent QA corpus

## Purpose
This corpus is an engineering regression suite for five observable text-level issue
families. It is not legal advice and does not encode a patent office's full legal test.

## Unit of annotation
One case is one source claim (or short claim context), one candidate generated output,
and one or more expected issue codes. Evidence spans are reserved for exact text
segments that support the expected code.

## Issue codes
- `CLAIM_LIMITATION_OMITTED`: a limitation explicitly configured as required is absent.
- `UNSUPPORTED_TECHNICAL_ASSERTION`: a configured technical feature occurs in candidate
  text but not in source text.
- `UNVERIFIED_PATENT_CITATION`: a citation identifier is not in the supplied evidence-ID
  list; this does not mean the document does not exist.
- `INVALID_CLAIM_DEPENDENCY`: a configured reference points to a missing/later claim.
- `ANTECEDENT_BASIS_MISSING`: configured definite terminology has no prior indefinite
  introduction in the candidate text.

## Severity
Severity is an initial engineering triage label only. It is not a legal materiality
assessment. The current corpus uses high for claim omission/unsupported additions and
medium for citation, dependency and antecedent signals.

## Provenance and review
Every current record is marked `synthetic_test_oracle`. No attorney, patent agent, or
independent annotator has adjudicated these records. The rationale explicitly records
that limitation. Before a real corpus is used, record annotator IDs, review timestamps,
jurisdiction, technology domain, source provenance, adjudication status, and reviewer
disagreement. Do not use generated labels as ground truth without expert review.

## Split and privacy
The 15 cases are a regression suite only. There are no train/dev/test splits. A future
corpus must be split by patent family or source document to avoid leakage. Use only
permissioned, de-identified material; do not transmit confidential or privileged
documents to an external model without authorization.
