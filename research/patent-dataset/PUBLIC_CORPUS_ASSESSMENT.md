# Public patent corpora: suitability assessment

**Status:** candidate-source review; no external corpus has been imported or relabelled.

## Why multiple sources are needed

The current 20-case AgentCanvas fixture set is synthetic. Public patent datasets can supply real patent text and, in some cases, examiner outcomes or prior-art links. Those fields are not automatically expert labels for the specific text-level failure codes in AgentCanvas. Preserve the source dataset's original task and annotation provenance; do not convert grant/rejection outcomes into claim-fidelity or antecedent-basis labels.

## Candidate sources

| Source | What it contributes | Fit for AgentCanvas | Important limitation |
|---|---|---|---|
| USPTO Patent Claims Research Dataset | Parsed claims, claim dependencies, and claim/document statistics for US grants (1976–2014) and published applications (2001–2014) | Strong starting point for claim segmentation, dependency parsing, and structural rule validation | It is not a labelled dataset of generated-output defects or expert annotations for our seven issue codes |
| Harvard USPTO Patent Dataset (HUPD) | Full application text, claims, metadata, and application decision status for US utility applications filed 2004–2014 | Useful for real-world claim/application text and carefully scoped outcome analyses | Decision status is not a claim-level explanation for each defect; verify current dataset terms before redistribution |
| PatentMatch | Claim-to-prior-art passage pairs based on EPO full-text documents and search reports | Useful for evidence retrieval and claim/prior-art passage matching | Its relevance labels concern prior-art matching, not whether a generated claim rewrite preserved every limitation |
| PANORAMA | Patent examination records with applications, citations, office actions, rejection rationales, and allowance trails | Promising for examination-process evaluation and traceable rejection-rationale tasks | Some rationale fields are machine-extracted from office actions; retain their provenance and human-validation status rather than treating every field as ground truth |
| PEDANTIC | A 14k-claim definiteness corpus with reasons for indefiniteness, extracted from office actions and subjected to a human validation study | Particularly relevant to a future definiteness/antecedent-basis sub-benchmark | Narrower task/domain (NLP-related applications); verify release access, version, license, and annotation details before ingestion |

## Recommended corpus strategy

1. Keep the 20 synthetic cases as a deterministic software regression suite only.
2. Add a separate, versioned real-document corpus with source URLs/IDs, jurisdiction, filing/publication dates, technology domain, and source licence/terms.
3. Build task-specific subsets: claim structure/dependency; prior-art passage retrieval; office-action rationale; and claim-text drafting signals. Do not pool labels across tasks.
4. For AgentCanvas-generated-output evaluation, create paired source-claim / candidate-output examples. Public historical patent text alone cannot supply the candidate-output side or labels for preservation errors.
5. Recruit at least two qualified annotators per item for the primary labels. Keep annotators blind to model identity and predictions.
6. Measure per-label agreement before adjudication (Cohen's kappa for two annotators on categorical labels; Krippendorff's alpha for multiple annotators or missing judgments). Report raw agreement and class prevalence too.
7. Have an independent adjudicator resolve disagreements; preserve both original labels and adjudicated labels.
8. Freeze a held-out test split by patent family or source document to reduce leakage. Keep all related family members in one split.
9. Do not send unpublished, confidential, privileged, or otherwise restricted patent material to external LLM providers without explicit authorization.

## Annotation record template

One record should include:

- `record_id`, `source_document_id`, `source_url`, `jurisdiction`, `technology_domain`, `publication_date`, `source_terms`
- `source_claim_text`, `candidate_output_text`, `evidence_text`, `evidence_span_start`, `evidence_span_end`
- `issue_code`, `severity`, `annotator_id`, `annotation_timestamp`, `confidence`, `rationale`
- `adjudication_status`, `adjudicator_id`, `adjudicated_label`, `split`, `dataset_version`

Annotator identity should be pseudonymous in released research data unless the annotator explicitly agrees to attribution.

## Sources

- USPTO, Patent Claims Research Dataset: https://www.uspto.gov/ip-policy/economic-research/research-datasets/patent-claims-research-dataset
- HUPD: https://patentdataset.org/
- PatentMatch dataset and code: https://hpi.de/naumann/projects/web-science/paar-patent-analysis-and-retrieval/patentmatch.html
- PANORAMA paper and dataset: https://arxiv.org/abs/2510.24774 and https://huggingface.co/datasets/LG-AI-Research/PANORAMA
- PEDANTIC paper: https://arxiv.org/abs/2505.21342

**Release gate:** do not report real-world model performance until the source terms, data lineage, label provenance, annotation agreement, adjudication, and held-out split have been independently checked.
