# Full-Text Method Card Template

```yaml
paper_id:
full_citation:
doi:
formal_status: journal | conference | preprint | thesis
venue:
year:
access_source:
evidence_level: A1 | A2 | B1 | B2 | C
fulltext_read_date:
reviewer:

problem:
robot_or_system:
fixed_or_floating_base:
dof:
task:

signals:
  measured: []
  estimated: []
  derived: []
  independent_redundancy: []

training:
  healthy_only:
  fault_labels_used:
  train_test_unit: episode | window | sample
  leakage_risk:

method:
  analytic_frontend:
  residual:
  network:
  chain_or_graph_structure:
  geometry_or_lie_usage:
  anomaly_head:
  threshold_or_sequential_rule:

outputs:
  detection:
  fault_family:
  joint_or_link_localization:
  severity_identification:
  rejection_or_ood:

statistics:
  false_alarm_metric:
  detection_delay:
  calibration:
  guarantee:

experiments:
  datasets: []
  real_robot:
  simulation:
  cross_context:
  cross_robot:
  sample_efficiency:
  baselines: []
  metrics: []

artifacts:
  code_url:
  data_url:
  license:
  reproduction_status:

key_equations_and_pages: []
key_tables_figures_pages: []
limitations_and_negative_results: []

collision_with_claims:
  C1:
  C2:
  C3:
  C4:
  C5:
  C6:

novelty_status: OCCUPIED | PARTIALLY_OCCUPIED | PLAUSIBLY_OPEN | UNKNOWN | FALSELY_FRAMED
reason:
confidence:
```

方法卡必须引用正文页码；不能仅依据摘要填写“未覆盖”。
