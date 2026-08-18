# Public Benchmark Command Plan

执行者应建立统一 CLI，示例：

```bash
python -m certo_fdi_reset.datasets.fetch --dataset voraus_ad --version 100hz
python -m certo_fdi_reset.datasets.audit --dataset voraus_ad
python -m certo_fdi_reset.baselines.run_native --dataset voraus_ad --baseline mvt_flow --profile smoke
python -m certo_fdi_reset.baselines.run_native --dataset voraus_ad --baseline mvt_flow --profile full
python -m certo_fdi_reset.baselines.run_matrix --dataset road --profile full
python -m certo_fdi_reset.candidates.run --dataset aursad --model chain_gnn_public --profile full
python -m certo_fdi_reset.evaluate.aggregate --run-root "$RUN_ROOT"
python -m certo_fdi_reset.decision --config configs/paper_reset.yaml
python scripts/build_review_packages.py --run-root "$RUN_ROOT"
```

具体命令可以调整，但必须有：fetch/audit/preprocess/train/evaluate/decision/package 分层，且所有命令写入 manifest。
