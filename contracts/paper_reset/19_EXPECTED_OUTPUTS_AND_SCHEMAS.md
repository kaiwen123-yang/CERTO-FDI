# Expected Outputs

## Literature

```text
literature_search_log.csv
literature_raw_export/
literature_deduplicated_library.csv
screening_decisions.csv
prisma_flow.csv
fulltext_access_manifest.csv
fulltext_method_cards/
literature_evidence_matrix.csv
nearest_neighbor_matrix.md
killer_paper_dossiers/
negative_search_log.md
claim_collision_matrix.md
novelty_decision_memo.md
verified_bibliography.bib
```

## Datasets

```text
public_dataset_registry_resolved.csv
dataset_license_matrix.csv
dataset_download_manifest.csv
dataset_schema_matrix.csv
dataset_split_manifest.csv
dataset_applicability_matrix.csv
public_data_known_issues.md
```

## Baselines

```text
native_baseline_reproduction.csv
universal_baseline_matrix.csv
baseline_deviation_ledger.csv
sample_efficiency_curves.csv
cross_context_metrics.csv
per_anomaly_metrics.csv
public_benchmark_manifest.json
baseline_reproduction_memo.md
```

## Candidate and decision

```text
candidate_adapter_matrix.csv
candidate_public_results.csv
geometry_increment_ablation.csv
combined_decision_evidence.json
paper_reset_decision_memo.md
claim_ledger_updated.csv
known_issues.md
run_manifest.json
```

所有 CSV 至少包含：

```text
run_id, git_sha, config_sha, dataset_id, dataset_version, data_manifest_sha,
split, model, seed, status, reproduction_level, provisional, metric, value, unit
```
