# Depth model survey evidence

This directory holds the supporting evidence for the Plan 068 literature survey
and GitHub issue #36. The survey cutoff is **2026-09-30**. Access dates describe
when a source was inspected; paper versions and release revisions identify the
evidence used. A current repository page does not by itself establish which
checkpoint produced a paper's result.

## Organization

Each `issue-NN` directory contains the search, model, benchmark and license
records for one independently reviewed section. The corresponding section
explains its sources, protocol limits and verification. The consolidated
inventories retain source provenance and reconcile exact model identities
across sections. Additional variants and contradictory observations remain
visible rather than being silently averaged or discarded.

The four root CSVs consolidate the section records without changing their scoped
identifiers or source fields. They are a reading/export view of the section data,
not additional independent evidence. Update them together with any corrected
section rows. `identity-links.csv` records explicit relationships using
`source_model_id,target_model_id,relation,rationale`. Both IDs resolve in
`models.csv`, except `not_applicable` for a screened lead with no audited target.
An unlisted pair is not an assertion of different families.

Only `same_release` denotes an exact duplicate release record. Same weights with
different inputs/implementations remain different experimental controls.
`family_only`, `paper_model_reference`, `paper_architecture_reference` and
`discovery_route` do not establish checkpoint equivalence. Refreshes, derived
models, retraining and unresolved mappings retain separate identities. Benchmark
observations retain evaluator provenance even when models share weights. The
verification note records the duplicate-observation check and material conflicts;
no family count or independent-repeat count is inferred from CSV row counts.

All CSV files are UTF-8 with a header row and standard CSV quoting. Fields are
strings. Multiple URLs or identifiers in a field are separated by semicolons.
Use `unknown` for genuinely unavailable information and `not_applicable` where
a field does not apply; explain material uncertainty in `notes`. Missing scores
are not zero-valued observations. Numerical benchmark values are decimal
strings interpreted together with their metric, unit and better direction.

The per-section identifiers begin with `iNN-`. A model identifier names an exact
variant/input mode within that section; it does not assert a distinct model
family. Protocol identifiers name an evaluation setting, including alignment
and input conditions. A matching metric name or dataset alone does not establish
that two protocols are comparable. Every benchmark and license model identifier
must resolve in the corresponding model inventory.

## Search records

Header:

```text
search_id,round,source_url,query_or_table,accessed_at,discovered_models,disposition,notes
```

| Field | Meaning |
| --- | --- |
| `search_id` | Unique record of a search or citation-following step. |
| `round` | Initial discovery, first or second table/reference expansion, or targeted gap review. |
| `source_url`, `query_or_table` | Actual entry point and query, table or reference inspected. |
| `accessed_at` | Inspection date. |
| `discovered_models` | Discovered names or scoped identifiers; cross-category leads may not yet have a local model row. |
| `disposition`, `notes` | Inclusion, exclusion, cross-reference, access failure, and the reason or coverage limit. |

A search record documents work actually performed. A list of suggested papers
or an accessible landing page is not evidence that every linked paper was read.

## Model records

Header:

```text
model_id,family,variant,category,input_regime,output_semantics,camera_requirements,parameters,release_status,paper_url,paper_version,code_url,code_revision,weights_url,weights_revision,environment,release_paper_difference,notes
```

| Fields | Meaning |
| --- | --- |
| `model_id`, `family`, `variant`, `category` | Scoped identity, family and exact backbone/checkpoint or input mode. |
| `input_regime`, `output_semantics`, `camera_requirements` | Required images/views/frames/sensors, depth or geometry meaning, and known/predicted cameras or focal information. |
| `parameters` | Published parameter count with its units and variant context, or unknown. |
| `release_status` | Whether the specified artifact is released, gated, paper-only or otherwise qualified. |
| `paper_url`, `paper_version` | Paper identity and version used. |
| `code_url`, `code_revision`, `weights_url`, `weights_revision` | Official implementation and exact asset provenance where established. An unknown revision must not be presented as a pinned release. |
| `environment` | Documented implementation/runtime requirements; no installed compatibility claim. |
| `release_paper_difference`, `notes` | Retraining, variant mismatch, dependency or input limitations, and other material qualifications. |

Comparison-only baselines also need identity records. A paper row with an
unspecified backbone can be recorded as such; it must not inherit the identity
of the project's chosen checkpoint.

## Benchmark observations

Header:

```text
observation_id,model_id,protocol_id,dataset,split,metric,value,unit,direction,input_regime,resolution,crop_mask,depth_range,alignment,training_regime,training_overlap,paper_url,paper_version,table_location,reporting_party,baseline_provenance,hardware,inference_settings,notes
```

| Fields | Meaning |
| --- | --- |
| `observation_id`, `model_id`, `protocol_id` | Unique observation and its model and evaluation identities. |
| `dataset`, `split` | Evaluation dataset/version and split where disclosed. |
| `metric`, `value`, `unit`, `direction` | Reported metric, numerical value, units and whether lower or higher is better. Ratios and percentages remain distinguishable. |
| `input_regime`, `resolution`, `crop_mask`, `depth_range` | Input/evaluation conditions, validity treatment and depth limits. |
| `alignment` | Scale, scale-and-shift or other alignment, its depth/disparity domain, and per-image/sequence/global scope where known. |
| `training_regime`, `training_overlap` | Zero-shot or adapted/fine-tuned conditions and disclosed evaluation-data overlap. |
| `paper_url`, `paper_version`, `table_location` | Exact primary source, table/page-or-section and row needed to check the value. |
| `reporting_party`, `baseline_provenance` | Who reports the number and whether it was rerun, copied, or unspecified. |
| `hardware`, `inference_settings` | Reported compute context, including precision, batch/view/frame count, steps or refinement where relevant. |
| `notes` | Conflicting protocol text, uncertain identity, reported anomalies and other comparison limits. |

Keep incompatible or ambiguous protocols in separate groups. Per-image
ground-truth scale fitting cannot establish absolute metric scale. A copied
baseline result is not an independent repeat. Runtime comparisons require the
reported hardware and inference conditions; these records contain no new host
measurements.

## License findings

Header:

```text
model_id,code_license,code_commercial,weights_license,weights_commercial,inference_and_output_terms,commercial_offer,commercial_contact,dependency_notes,code_license_url,weights_license_url,terms_source_urls,accessed_at,notes
```

| Fields | Meaning |
| --- | --- |
| `model_id` | Exact artifact or combination being assessed. |
| `code_license`, `code_commercial` | Code terms and their commercial-use disposition. |
| `weights_license`, `weights_commercial` | Separate checkpoint terms and commercial-use disposition. |
| `inference_and_output_terms` | Terms governing commercial inference and any explicit output-use provisions; distinguish them from output ownership. |
| `commercial_offer`, `commercial_contact` | An explicit author offer or inquiry channel, or an unresolved/absent finding. A generic address is not an offer. |
| `dependency_notes` | Material base-model, adapter, refiner and dependency qualifications supported by the inspected sources. |
| `code_license_url`, `weights_license_url`, `terms_source_urls` | Primary documents supporting each conclusion. |
| `accessed_at`, `notes` | Date and remaining ambiguity, conflicts or lineage limitations. |

Use permission, restriction or unresolved findings supported by actual terms.
Neither an arXiv publication license nor a code license automatically licenses
model weights. A restriction on commercial inference does not automatically
settle every later use or copyright status of an output. Missing terms and
conflicting release notices remain explicit limitations.

## Verification boundary

The user selected report and source checks. Verify ordinary CSV parsing and
referential consistency, every reported numerical value against its source,
variant/release identities, licensing findings, comparison compatibility and
the trace from recommendations to evidence. Record outcomes in the research
sections and final verification note. This work does not introduce an
executable validation subsystem or run model/application tests.
