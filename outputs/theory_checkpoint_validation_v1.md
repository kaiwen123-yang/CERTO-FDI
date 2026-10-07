# 理论阶段包：实际ZIP验收 v1

2026-10-07。实际文件 `CERTO_FDI_THEORY_CHECKPOINT_20261007_V1.zip`，780548 bytes，SHA256 `55e5155cb5dc3e7cb40e5e3abfffa61fa438b197c7bc68213b27f286ede03ac3`，98个文件（含manifest）。这是局部理论阶段包，不是TAC最终交付或完整D2-a。

根代理从这个实际ZIP新解压到 `work/theory_checkpoint_verify_v1/`，先CRC/路径检查，再在新 `python -S` 进程执行 `verify_theory.py`。97个payload哈希全部匹配；包内全部11个精确检查脚本各自用新的标准库进程执行，exit=0，计算结果与包内保存的JSON逐项一致，failures=[]。保存回执为 `theory_checkpoint_validation_v1.json`，全过程约5.3秒。不以原工作树的结果冒充这次解压执行。

范围包括AR(1)边界/逆界/达到、iid局部审查、一阶/矩阵物理输入projection、singular共支持、recoverable新日历、6个非零weighted-repair，以及settling候选。它们是精确有限检查，不能代替全称证明或独立数学审查。recoverable Theta补充在打包时仍待独立接受，有限PASS不自动升级证明状态。

TeX文章未编译通过；内置compiler是平台目录错误，非已确认的源码错误。图的PDF由Matplotlib生成、其实际descendant fonts嵌入，但不是文章PDF。可选图recipe需要Matplotlib/Pillow及当前skill的visual QA helper，不属于标准库验收入口。

不包含正在运行的全部6R大witness、原R1大ZIP或下载的版权论文PDF。完整400行D2-a、正式IEEE版式/页数、剩余最近邻全文、完整技术稿反方审查和最终ZIP验收仍待推进。
