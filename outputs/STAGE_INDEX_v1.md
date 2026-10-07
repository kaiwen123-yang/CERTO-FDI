# 分阶段审查索引 v1

这是 `kaiwen123-yang/CERTO-FDI` 发布材料的人工审查入口。路径相对仓库根目录保存；本文件位于 `outputs/`，因此链接用 `../outputs/`、`../references/` 等。完整 SHA、范围和角色见 [STAGE_INDEX_v1.json](STAGE_INDEX_v1.json)，阅读顺序见 [GITHUB_REVIEW_GUIDE_v1.md](GITHUB_REVIEW_GUIDE_v1.md)。

**冻结状态：R8/12页；full400未完成；四全文比较缺口开放；PiPER仅静态准备。未在本次导航编写中运行测试、科学或远程操作。Release URL需由实际发布者补入，不预填虚构链接。**

| 阶段 | 状态／证据层 | 首入口及SHA前12位 | 对应独审 | 最关键质疑 |
|---|---|---|---|---|
| S00 当前稿与贡献／来源边界 | `R8_SOURCE_PDF_LAYOUT_ACCEPTED_WITH_OPEN_SOURCE_GAPS`；manuscript_snapshot, layout_review, source_support_audit | [certo_fdi_control_memory_draft_v1.pdf](../outputs/certo_fdi_control_memory_draft_v1.pdf)；`e148cf867fb3` | [manuscript_revision8_integration_review_v1.md](../outputs/manuscript_revision8_integration_review_v1.md) | 所述贡献是否依赖尚未取得全文的历史排除？当前固定信息合同是否被写成普遍主动诊断/机器人下界？ |
| S01 继承R1物理、比较系统与固定实例 | `ACTUAL_INHERITED_R1_FIXED_INSTANCE_VERIFIER_PASS`；inherited_model_and_certificates, actual_fixed_instance_verification | [r1_source_scope.md](../references/audit_20261007/r1_source_scope.md)；`8c67793ed781` | [post_move_point_bound.md](../references/audit_20261007/post_move_point_bound.md) | 是否将Gaussian comparator、平均读出半径或固定R1证书直接移用到真实非线性统计量、post-move point或新日历？ |
| S02 共同支持合同、主定理与zero score容量 | `MATHEMATICAL_PROOF_REVIEW_ACCEPTED_FIXED_CONTRACT`；mathematical_proof_review | [m2s_problem_contract_v1.md](../outputs/m2s_problem_contract_v1.md)；`80a5a5d64343` | [m2s_independent_review_v1.md](../outputs/m2s_independent_review_v1.md) | all-calendar converse、双向可重复exact-k上界、真实rowspace、全输入总质量修复与1/2 gap偏移是否都保留？是否误以伪逆替换等于白化，或score preserved等于P=I？ |
| S03 同物理输入的control beta与共同SPD uniform设计 | `MATHEMATICAL_CONTROL_PROOF_REVIEW_ACCEPTED_RESTRICTED_FAMILY`；mathematical_proof_review, finite_exact_example | [control_memory_example_v1.md](../outputs/control_memory_example_v1.md)；`5eb2f17dcedf` | [compact_controller_uniform_review_v1.md](../outputs/compact_controller_uniform_review_v1.md) | 是否只是改了噪声/信息权限？uniform little-oh有共同resolvent/tail与packing依据吗？是否错误推广到rank-changing singular族、noisy/forced return或有限H最优控制？ |
| S04 Gaussian接口、bounded-even与固定端点风险推论 | `DERIVED_FIXED_ENDPOINT_PROOF_REVIEW_ACCEPTED`；mathematical_proof_review, established_Gaussian_interface | [fixed_endpoint_horizon_corollary_v1.md](../outputs/fixed_endpoint_horizon_corollary_v1.md)；`47e9f15a41e9` | [fixed_endpoint_horizon_corollary_review_v1.md](../outputs/fixed_endpoint_horizon_corollary_review_v1.md) | 是否从sup阈值直接假设可实现test、漏排更早H，或将整数O(1)写成Theta(1)/统一正下界？两假设的完整path预算是否分别支付？ |
| S05 R6有限精确检查与V2理论checkpoint | `ACTUAL_ARCHIVE_FINITE_CHECKS_PASS_NOT_UNIVERSAL_PROOF`；finite_exact_checks, actual_archive_hash_and_extraction | [theory_checkpoint_archive_receipt_v2.json](../outputs/theory_checkpoint_archive_receipt_v2.json)；`ea743bcdab9d` | [m1_independent_review_v1.md](../outputs/m1_independent_review_v1.md) | 检查实际覆盖哪些有限矩阵/日历/非零repair？有没有把PASS数量、包hash或有限网格拟合当成全称证明/完整科学复现？ |
| S06 冻结D2 complete-subgrid与代表实例 | `FROZEN_FINITE_SUBGRID_EVIDENCE_ACCEPTED_NOT_FULL400`；finite_non_linear_risk_certificates, frozen_small_metadata_binding | [d2a_readout_figure_data_v1.json](../outputs/d2a_readout_figure_data_v1.json)；`8022e863c9b7` | [d2a_readout_figure_review_v1.md](../outputs/d2a_readout_figure_review_v1.md) | 零方向缺证书是否被填成power=0？point零保证是否被误称真实功效0/不可检测？非线性remainder/event是否双侧支付，H100与H160是否被混成全日历最短时间？ |
| S07 H160实际ZIP、新ROOT与有记录的环境恢复 | `ACTUAL_SCOPED_SCIENCE_PAIR_ACCEPTED_AFTER_DOCUMENTED_IO_RECOVERY`；actual_scientific_replay_fixed_cases, actual_archive_payload_hashes, documented_operational_recovery | [d2a_science_zip_rehearsal_v1.md](../outputs/d2a_science_zip_rehearsal_v1.md)；`caab48175695` | [d2a_science_zip_rehearsal_review_v1.md](../outputs/d2a_science_zip_rehearsal_review_v1.md) | 新receipt是否来自旧工作树或旧receipt拷贝？完整方差/mean/event/risk是否实际重算？首轮失败是否被擦掉，恢复源码是否被假称已在原ZIP内？ |
| S08 full400尚未闭合与未来正式科学包门禁 | `NOT_COMPLETED_FUTURE_FULL400_BRANCH_NOT_EXECUTED`；pending_complete_grid, limited_IO_and_coverage_review | [full_d2a_release_contract_v1.md](../outputs/full_d2a_release_contract_v1.md)；`d633636c7d14` | [d2a_archive_view_bridge_review_v1.md](../outputs/d2a_archive_view_bridge_review_v1.md) | 是否每个science identity都对应actual ZIP canonical目录并有fresh full verifier？cleanup后metadata是否仍来自独立原ZIP视图？有没有忽略unfinished前驱/失败、或将presence当科学证明？ |
| S09 PiPER H官方静态接口预备 | `OFFICIAL_PINNED_STATIC_PREPARATION_ONLY_NO_HARDWARE`；official_static_source_interface_review | [piper_h_interface_protocol_v1.md](../outputs/piper_h_interface_protocol_v1.md)；`ebf843c1195e` | [piper_h_protocol_review_v1.md](../outputs/piper_h_protocol_review_v1.md) | 是否把异步缓存/估计torque当成已知full-state/common-input Gaussian合同，或把共同固定p的IID binomial例当varying-context最坏误报/真实硬件保证？ |

## 每阶段的阅读材料

### S00 当前稿与贡献／来源边界

当前R8源稿与12页PDF已有实际编译/逐页排版及局部整合审查；不等于投稿就绪或穷尽历史新颖性。13条书目与17项近邻对照须按各报告原版本/全文范围解释，四项全文比较仍开放。

- 主材料：[certo_fdi_control_memory_draft_v1.pdf](../outputs/certo_fdi_control_memory_draft_v1.pdf)、[certo_fdi_control_memory_draft_v1.tex](../outputs/certo_fdi_control_memory_draft_v1.tex)、[citation_preflight_v1.md](../outputs/citation_preflight_v1.md)、[citation_support_matrix_v1.json](../outputs/citation_support_matrix_v1.json)。
- 独立审查：[manuscript_revision8_integration_review_v1.md](../outputs/manuscript_revision8_integration_review_v1.md)、[manuscript_compile_layout_status_v4.json](../outputs/manuscript_compile_layout_status_v4.json)。
- 配套源码／证据：[manuscript_revision_8_receipt.json](../outputs/manuscript_revision_8_receipt.json)、[tac_contribution_argument_v1.md](../outputs/tac_contribution_argument_v1.md)、[novelty_control_memory_collision_v1.md](../outputs/novelty_control_memory_collision_v1.md)、[submission_bibliography_verified_v1.tex](../outputs/submission_bibliography_verified_v1.tex)、[tac_format_preflight_v1.md](../outputs/tac_format_preflight_v1.md)。
- 当前R8查找标签：`sf:introduction`、`sf:conclusion`。

**质疑入口：**所述贡献是否依赖尚未取得全文的历史排除？当前固定信息合同是否被写成普遍主动诊断/机器人下界？

### S01 继承R1物理、比较系统与固定实例

原R1实际归档已有fresh verifier exit0和前后input绑定，限实际固定方向/有限确定性日历。源审查明确完整时钟、入段/return、两侧误差与point读出连接；未补齐真实六关节三阶同伦管，也不是有色锐极小极大定理。

- 主材料：[r1_source_scope.md](../references/audit_20261007/r1_source_scope.md)、[r1_verification.md](../references/audit_20261007/r1_verification.md)、[r1_verification_receipt.json](../references/audit_20261007/r1_verification_receipt.json)。
- 独立审查：[post_move_point_bound.md](../references/audit_20261007/post_move_point_bound.md)。
- 配套源码／证据：[post_move_point_support.json](../references/audit_20261007/post_move_point_support.json)、[next_proofs.tex](../references/audit_20261007/next_proofs.tex)。
- Release资产：`CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip`；SHA `f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b`；114986329 bytes。实际URL尚待发布者填写。

**质疑入口：**是否将Gaussian comparator、平均读出半径或固定R1证书直接移用到真实非线性统计量、post-move point或新日历？

### S02 共同支持合同、主定理与zero score容量

固定known Schur plant、满列G/B在rangeG、真实retained全状态、同输入通道、全clock/path和free-level/rate合同。beta>0主定理匹配所有calendar的H^(5/2)首系数；beta=0为Theta(H^2)，无sharp quadratic系数。score容量不是全部latent input恢复。正文附录内联完整主证明。

- 主材料：[m2s_problem_contract_v1.md](../outputs/m2s_problem_contract_v1.md)、[m2s_singular_memory_theorem_v1.md](../outputs/m2s_singular_memory_theorem_v1.md)、[m2s_recoverable_order_v1.md](../outputs/m2s_recoverable_order_v1.md)、[m2s_two_regime_section_v1.tex](../outputs/m2s_two_regime_section_v1.tex)。
- 独立审查：[m2s_independent_review_v1.md](../outputs/m2s_independent_review_v1.md)、[m2s_recoverable_order_review_v1.md](../outputs/m2s_recoverable_order_review_v1.md)、[m2s_regime_integration_review_v1.md](../outputs/m2s_regime_integration_review_v1.md)、[submission_consolidation_review_v1.md](../outputs/submission_consolidation_review_v1.md)。
- 配套源码／证据：[m2_problem_contract_v1.md](../outputs/m2_problem_contract_v1.md)、[m2_controlled_memory_theorem_v1.md](../outputs/m2_controlled_memory_theorem_v1.md)、[m2_independent_review_v1.md](../outputs/m2_independent_review_v1.md)、[memory_asymmetric_repair_supplement_v1.md](../outputs/memory_asymmetric_repair_supplement_v1.md)、[submission_consolidation_map_v1.md](../outputs/submission_consolidation_map_v1.md)。
- 当前R8查找标签：`sf:model`、`sf:two-regime`、`sf:capacity`、`sf:spd`、`sf:geometry`、`sf:positive-proof`、`sf:zero-proof`。

**质疑入口：**all-calendar converse、双向可重复exact-k上界、真实rowspace、全输入总质量修复与1/2 gap偏移是否都保留？是否误以伪逆替换等于白化，或score preserved等于P=I？

### S03 同物理输入的control beta与共同SPD uniform设计

完整记录的信息中性与missing-span控制器罚分开；equal poles不固定beta。共同固定B/Q正定、紧致strict-Schur控制器族有uniform余项及joint leading inf；一般不假设k连续或inf达到。settling例只在已证齐次模型及标量候选范围内。

- 主材料：[control_memory_example_v1.md](../outputs/control_memory_example_v1.md)、[controller_settling_tradeoff_v1.md](../outputs/controller_settling_tradeoff_v1.md)、[compact_controller_uniform_bridge_v1.md](../outputs/compact_controller_uniform_bridge_v1.md)、[control_settling_figure_v1.pdf](../outputs/control_settling_figure_v1.pdf)。
- 独立审查：[compact_controller_uniform_review_v1.md](../outputs/compact_controller_uniform_review_v1.md)。
- 配套源码／证据：[control_memory_checks_v1.py](../outputs/control_memory_checks_v1.py)、[control_memory_checks_v1.json](../outputs/control_memory_checks_v1.json)、[controller_settling_checks_v1.py](../outputs/controller_settling_checks_v1.py)、[controller_settling_checks_v1.json](../outputs/controller_settling_checks_v1.json)、[control_settling_figure_data_v1.csv](../outputs/control_settling_figure_data_v1.csv)、[control_settling_figure_caption_v1.md](../outputs/control_settling_figure_caption_v1.md)、[control_settling_figure_portable_v2.py](../outputs/control_settling_figure_portable_v2.py)、[portable_figure_recipe_receipt_v2.md](../outputs/portable_figure_recipe_receipt_v2.md)。
- 当前R8查找标签：`sf:control`、`sf:settling`、`sf:uniform`、`sf:control-proofs`。

**质疑入口：**是否只是改了噪声/信息权限？uniform little-oh有共同resolvent/tail与packing依据吗？是否错误推广到rank-changing singular族、noisy/forced return或有限H最优控制？

### S04 Gaussian接口、bounded-even与固定端点风险推论

成熟Gaussian凸接口提供固定calendar风险换算；bounded-even为固定envelope下的次阶扰动。新增endpoint推论只解释既有亏损律：正beta相对oracle的确定性整数端点excess为sqrt(H_or)首项，zero beta仅0<=excess=O(1)。不是独立主要创新、sequential/ARL/E[tau]或非线性D2无穷时域结论。

- 主材料：[fixed_endpoint_horizon_corollary_v1.md](../outputs/fixed_endpoint_horizon_corollary_v1.md)、[fixed_endpoint_horizon_corollary_v1.tex](../outputs/fixed_endpoint_horizon_corollary_v1.tex)、[bounded_even_bias_corollary_v1.md](../outputs/bounded_even_bias_corollary_v1.md)。
- 独立审查：[fixed_endpoint_horizon_corollary_review_v1.md](../outputs/fixed_endpoint_horizon_corollary_review_v1.md)、[bounded_even_bias_review_v1.md](../outputs/bounded_even_bias_review_v1.md)、[manuscript_revision8_integration_review_v1.md](../outputs/manuscript_revision8_integration_review_v1.md)。
- 配套源码／证据：[fixed_endpoint_horizon_corollary_v1.json](../outputs/fixed_endpoint_horizon_corollary_v1.json)、[next_proofs.tex](../references/audit_20261007/next_proofs.tex)。
- 当前R8查找标签：`sf:risk`、`sf:fixed-endpoint-risk`、`sf:endpoint-proof`、`sf:even-section`、`sf:even-proof`。

**质疑入口：**是否从sup阈值直接假设可实现test、漏排更早H，或将整数O(1)写成Theta(1)/统一正下界？两假设的完整path预算是否分别支付？

### S05 R6有限精确检查与V2理论checkpoint

不可变V2 checkpoint保存R6/11页源与PDF：212 members/210 payload，实际新提取及11个standalone exact checks通过，图metadata有限核验。它不含当前R8/endpoint插入，也未执行大型D2科学replay。有限有理数/矩阵/日历反例检查不能替代所有calendar的数学证明。

- 主材料：[theory_checkpoint_archive_receipt_v2.json](../outputs/theory_checkpoint_archive_receipt_v2.json)、[theory_checkpoint_validation_v2.md](../outputs/theory_checkpoint_validation_v2.md)、[theory_checkpoint_validation_v2.json](../outputs/theory_checkpoint_validation_v2.json)、[8eaa707da6df0c477a946e596ba3bc05522f249e93f806e54288559db55e0e6e.tex](../references/manuscript_working_history/8eaa707da6df0c477a946e596ba3bc05522f249e93f806e54288559db55e0e6e.tex)。
- 独立审查：[m1_independent_review_v1.md](../outputs/m1_independent_review_v1.md)、[m2_independent_review_v1.md](../outputs/m2_independent_review_v1.md)、[m2s_independent_review_v1.md](../outputs/m2s_independent_review_v1.md)。
- 配套源码／证据：[theory_checkpoint_archive_receipt_v1.json](../outputs/theory_checkpoint_archive_receipt_v1.json)、[memory_asymmetric_repair_checks_v1.py](../outputs/memory_asymmetric_repair_checks_v1.py)、[memory_asymmetric_repair_checks_v1.json](../outputs/memory_asymmetric_repair_checks_v1.json)。
- 当前R8查找标签：`sf:verification`。
- Release资产：`CERTO_FDI_THEORY_CHECKPOINT_20261007_V2.zip`；SHA `6ab32cb85ebc7befd6410974b6781d97f5285147f13f19a744d1d7cf03cbb99c`；1919557 bytes。实际URL尚待发布者填写。

**质疑入口：**检查实际覆盖哪些有限矩阵/日历/非零repair？有没有把PASS数量、包hash或有限网格拟合当成全称证明/完整科学复现？

### S06 冻结D2 complete-subgrid与代表实例

prescribed terminal-balanced H={40,60,80,100,120,160,200}、两读出共14分类/12数值行，38小叶绑定。H40无风险证书保留missing；所有失败/未达目标保留。H100/26s是该列网格first certified，H160/41s满足原>=3完整块选例准则；H120历史保留。V+是规定Gaussian-comparator统计量的方差上界。

- 主材料：[d2a_readout_figure_data_v1.json](../outputs/d2a_readout_figure_data_v1.json)、[d2a_readout_figure_v1.pdf](../outputs/d2a_readout_figure_v1.pdf)、[d2a_readout_figure_caption_v1.md](../outputs/d2a_readout_figure_caption_v1.md)、[d2a_protocol_v1.md](../outputs/d2a_protocol_v1.md)。
- 独立审查：[d2a_readout_figure_review_v1.md](../outputs/d2a_readout_figure_review_v1.md)、[d2a_mean_risk_review_v1.md](../outputs/d2a_mean_risk_review_v1.md)、[d2a_three_block_example_review_v1.md](../outputs/d2a_three_block_example_review_v1.md)。
- 配套源码／证据：[d2a_readout_figure_v1.py](../outputs/d2a_readout_figure_v1.py)、[d2a_readout_figure_qa_v1.json](../outputs/d2a_readout_figure_qa_v1.json)、[d2a_readout_figure_review_v1.json](../outputs/d2a_readout_figure_review_v1.json)、[d2a_source_map_v1.md](../outputs/d2a_source_map_v1.md)、[manuscript_revision7_integration_review_v1.md](../outputs/manuscript_revision7_integration_review_v1.md)。
- 当前R8查找标签：`sf:verification`、`sf:readout-figure`。

**质疑入口：**零方向缺证书是否被填成power=0？point零保证是否被误称真实功效0/不可检测？非线性remainder/event是否双侧支付，H100与H160是否被混成全日历最短时间？

### S07 H160实际ZIP、新ROOT与有记录的环境恢复

实际296443279-byte ZIP，fresh R1一次/463文件，同一新ROOT两个distinct readout各完整full-S一次；avg77.6347s/targetPASS，point78.9169s/有效证书未达目标。48payload及47原输入前后绑定。原case非OS ReadOnly；只证明本轮字节稳定。首-File清理失败、第二longpath后置hash失败及外部恢复源码全部保留。

- 主材料：[d2a_science_zip_rehearsal_v1.md](../outputs/d2a_science_zip_rehearsal_v1.md)、[d2a_science_zip_rehearsal_receipt_v1.json](../outputs/d2a_science_zip_rehearsal_receipt_v1.json)、[d2a_science_zip_rehearsal_v1.json](../outputs/d2a_science_zip_rehearsal_v1.json)。
- 独立审查：[d2a_science_zip_rehearsal_review_v1.md](../outputs/d2a_science_zip_rehearsal_review_v1.md)、[d2a_science_zip_rehearsal_review_v1.json](../outputs/d2a_science_zip_rehearsal_review_v1.json)。
- 配套源码／证据：[d2a_science_zip_rehearsal_v1.py](../outputs/d2a_science_zip_rehearsal_v1.py)、[d2a_science_zip_rehearsal_resume_v1.py](../outputs/d2a_science_zip_rehearsal_resume_v1.py)、[d2a_science_zip_rehearsal_finalize_v1.py](../outputs/d2a_science_zip_rehearsal_finalize_v1.py)、[d2a_native_owned_case_cleanup_v1.py](../outputs/d2a_native_owned_case_cleanup_v1.py)、[d2a_science_zip_rehearsal_precheck_v1.json](../outputs/d2a_science_zip_rehearsal_precheck_v1.json)、[FAILURE_SCOPED_REHEARSAL.json](../outputs/d2a_pair_rehearsal_logs_e9098928/FAILURE_SCOPED_REHEARSAL.json)、[FAILURE_SCOPED_RESUME.json](../outputs/d2a_pair_rehearsal_logs_e9098928/FAILURE_SCOPED_RESUME.json)、[D2A_H160_TERMINAL_BALANCED_AVERAGE250_fresh_receipt.json](../outputs/d2a_pair_rehearsal_logs_e9098928/D2A_H160_TERMINAL_BALANCED_AVERAGE250_fresh_receipt.json)、[D2A_H160_TERMINAL_BALANCED_POINT_LAST_FAST_READ_fresh_receipt.json](../outputs/d2a_pair_rehearsal_logs_e9098928/D2A_H160_TERMINAL_BALANCED_POINT_LAST_FAST_READ_fresh_receipt.json)。
- Release资产：`D2A_H160_TERMINAL_PAIR_SCIENCE_REHEARSAL_V1.zip`；SHA `c5dfadbb4c914299fa502b4549158f8b2d0adae0d1f690cd06066d45b4c39f4f`；296443279 bytes。实际URL尚待发布者填写。

**质疑入口：**新receipt是否来自旧工作树或旧receipt拷贝？完整方差/mean/event/risk是否实际重算？首轮失败是否被擦掉，恢复源码是否被假称已在原ZIP内？

### S08 full400尚未闭合与未来正式科学包门禁

本发布冻结阶段没有完成400行/全部canonical科学replay。actual-ZIP presence、完整body hash、数学verifier、CSV/direction/case/fresh-replay覆盖是不同门。V3保留V2及GO/OS quiescence/metadata/caps/coverage门，仅新增Windows native cleanup及版本名；真实pair不替代未来full driver。

- 主材料：[full_d2a_release_contract_v1.md](../outputs/full_d2a_release_contract_v1.md)、[package_full_d2a_release_v3.py](../outputs/package_full_d2a_release_v3.py)、[d2a_full_grid_acceptance_v2.py](../outputs/d2a_full_grid_acceptance_v2.py)、[d2a_archive_coverage_gate_v1.py](../outputs/d2a_archive_coverage_gate_v1.py)。
- 独立审查：[d2a_archive_view_bridge_review_v1.md](../outputs/d2a_archive_view_bridge_review_v1.md)、[d2a_full_grid_acceptance_review_v1.md](../outputs/d2a_full_grid_acceptance_review_v1.md)、[d2a_science_zip_rehearsal_review_v1.md](../outputs/d2a_science_zip_rehearsal_review_v1.md)。
- 配套源码／证据：[full_d2a_release_contract_v1.json](../outputs/full_d2a_release_contract_v1.json)、[d2a_archive_view_bridge_v1.md](../outputs/d2a_archive_view_bridge_v1.md)、[d2a_archive_coverage_gate_addendum_v1.md](../outputs/d2a_archive_coverage_gate_addendum_v1.md)、[d2a_archive_csv_cap_addendum_v1.md](../outputs/d2a_archive_csv_cap_addendum_v1.md)、[package_full_d2a_release_v2.py](../outputs/package_full_d2a_release_v2.py)、[d2a_archive_witness_view_v1.py](../outputs/d2a_archive_witness_view_v1.py)。

**质疑入口：**是否每个science identity都对应actual ZIP canonical目录并有fresh full verifier？cleanup后metadata是否仍来自独立原ZIP视图？有没有忽略unfinished前驱/失败、或将presence当科学证明？

### S09 PiPER H官方静态接口预备

官方pyAgxArm固定commit841a625f5f4920e776f20b934eb13048b747e6d0的定向静态核查与准备协议。torque为电流换算、缓存非新RX、角度aggregate可能部分/default0且timestamp非max；没有import/install/run SDK、CAN连接、机器人动作或实测。

- 主材料：[piper_h_interface_protocol_v1.md](../outputs/piper_h_interface_protocol_v1.md)、[piper_h_source_audit_v1.json](../outputs/piper_h_source_audit_v1.json)。
- 独立审查：[piper_h_protocol_review_v1.md](../outputs/piper_h_protocol_review_v1.md)、[piper_h_protocol_review_v1.json](../outputs/piper_h_protocol_review_v1.json)。

**质疑入口：**是否把异步缓存/估计torque当成已知full-state/common-input Gaussian合同，或把共同固定p的IID binomial例当varying-context最坏误报/真实硬件保证？

## 版本与来源提醒

- 当前主稿：R8 source `2245714e5b92c5e36039a688f453b477256aa57df15f97a783442ea2bacbfdc1`；PDF `e148cf867fb38deef1f91bcb8aabc5c3cf6d1c7786d9cf3b88f07c01d8aae30c`；12页。作者资料/bios/photos尚未完整，页数与排版通过不是TAC ready。
- V2 checkpoint：R6 source `8eaa707da6df0c477a946e596ba3bc05522f249e93f806e54288559db55e0e6e`；PDF `c8e02b022d0c875163499f5a45ff374208376702f1176da66f02bd08665b6195`；11页，不含当前R8。当前R8增加已审endpoint推论并采用R7的H160代表例；H100首网格与H120历史均保留。
- 四项全文缺口：Esna Ashari / Nikoukhah / Campbell，*Effects of feedback on active fault detection*（2012）；Esna Ashari / Nikoukhah / Campbell，*Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach*（2012）；Cheng / Steinberg，*Trend robust two-level factorial designs*（1991）；Coster / Cheng，*Minimum Cost Trend-Free Run Orders of Fractional Factorial Designs*（1988）。身份/metadata/snippets不等于主定理覆盖排除。
- 索引只提供入口；各stage实际source/case清单以该stage的manifest、receipt和Release资产为准。后续发布新stage必须新增冻结状态/实际验收，不能改写旧stage历史。
