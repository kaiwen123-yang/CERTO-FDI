# M2S 两 regime 英文片段集成一致性审查 v1

2026-10-07。审查者：novelty_theorems。只读最终 fragment、交付 receipt、已接受数学来源和主稿 revision2；未改主稿、fragment、合同、checks 或根台账。没有新文献检索、新理论证明或旧大表复跑。

**结论：冻结英文 fragment 与已接受 M2S/Θ(H²) MD 的公式、量词及信息合同一致，可以内联到主稿。没有承重数学不一致。** 静态标签/字节/环境检查通过；主稿共同 SPD 的 compact-controller uniform 结论没有被扩展到奇异 rank 族。实际合并后的整稿与编译状态须由根另作版本绑定；本报告不宣称未读到的合并稿或 PDF 已通过。

## 1. 版本绑定

| 来源 | SHA256 |
|---|---|
| m2s_two_regime_section_v1.tex | 9e7bb4513007c9226f315e5e58ee661f556a7097d26fb31030aefc136fb03b7f |
| m2s_two_regime_section_receipt_v1.md | 60b2b9646b087f991779eea4369f869c928ed79ded022a985301c577293d86e4 |
| certo_fdi_control_memory_draft_v1.tex，revision2 | 3490f6339e4772521fa7f52db3af64f2e9ad850e379e915bd563f00b2e6273dd |
| m2s_problem_contract_v1.md | 80a5a5d643432f54f1a2d9f3dc7a9e374528358c18e10beb6b0e1ac1d5b9e7d5 |
| m2s_singular_memory_theorem_v1.md | 8ff2de70274973e4a9e104b26a5bf4be14e0e742998f2c562f6023e6316ab431 |
| m2s_recoverable_order_v1.md | 5b04f87f23fbfe1d2bc1fb1fbb791e783a47e029c7cdf130e1c000dd22d0f4f1 |
| m2s_independent_review_v1.md | 83f711812f92bd0cfe4f0ed5e158e8ff5c9005cf58006613fec25599a640c448 |
| m2s_recoverable_order_review_v1.md | c32efb758b39e3b3f1d11e8219ee365f50fb33f84eb44857739620d8e99571c8 |

Fragment、receipt 和 revision2 主稿哈希现场复验；472 行 fragment 全文实际读取。下文 fragment 行号绑定此版本。证明来源与既有审查沿前两次接受的冻结 MD，不改变其历史 checks 覆盖。

## 2. 数学与量词逐段对应

| Fragment 行号/标签 | 对应冻结内容 | 核查结论 |
|---|---|---|
| 14–38，m2sreg:plant | M2S 合同 §1–3，Θ supplement §1 | 固定已知 Schur A_K、full-column G、非零 B∈rangeG、known initialized prefix、两侧 rate r/2/free level、完整 input z、held±1/known missing g、诊断无 fast-state/command 旁路均保留。上界明示双向 reusable/concatenable exact-k profiles，可在预定起点执行；noise 前确定 calendar。 |
| 39–57，interval/information | M2S(P1)–(P2)、oracle | m=k+1 含 missing 和 right retained input；真正 P_m=H_mᵀW_m†H_m、terminal 未读 inputs 的零列、F/2、inf 全路径和 sup 日历均一致。不是 observed-trace rate 或假 state reset；sup 不暗含 finite-H attainment。 |
| 59–98，theorem/capacity | M2S(T1)–(T4)、Θ theorem R | positive 系数 (√2/5)√(Fβ_k r)η^{3/2} 与 ξ*=2β_kη/(Fr) 正确；zero 为 cH²≤D*≤CH²，明确无 H² sharp constant、fixed A_K/G/B；k<ν_R≤dimR∞−p+1≤d−p+1 正确。 |
| 100–143，common support/gamma | M2S §2–3 | 所有 means 在 rangeL_R；reduced SVD 给真实 standard supported Gaussian 和半平方 KL；可逆 predictor 左乘保留 rowspace，没有 pseudoinverse congruence；先 range 稳定再 inverse order，Γ 只为 fixed plant。 |
| 145–169，score/tail/capacity | M2S §4 | Constant ray rowspace 等价、β 非降、β_ℓ/ℓ→F、ζ 与 reached subspace 正交和 stable contradiction一致。p=d 时 β_k>0，不能把 β0 说成全部 latent inputs 恢复。 |
| 173–233，affine/positive converse | M2S §5–6 与主 M2 proof | Terminal dominance、L₁=−MᵀW†N、全日历 cross O(H²)、同一个 T 只 split 一次、cross-macro missing budget、tent full-path 及 F/1/2 因子一致。π-uniform 表述均在 fixed plant 内。 |
| 235–314，observable repair/upper | M2S §7–8 | Local levels 明示只是 auxiliary dual，不冒充全局 healthy path；baseline zero mass；P₁=I_p（非 I_d）、D≥F(2n−2)、N²/D、support correction 和真实 W†H v pullback 保留。Pair centers 1/2±(n+k)/2 及各 affine cross/factor 2 正确，U3 和优化 ξ 与 MD 一致。 |
| 316–385，zero upper | Θ supplement §3 | 全输入累计 M_t 包括 missing profile；offline threshold calendar，post singleton≥H/(k+2)；β0 只去 constant amplitude，slope norm loss O(H)；Abel→N=O(H)、D=Ω(H)、global exact mass repair、完整 free-level support O(H²) 和 Fenchel 因子正确。 |
| 387–460，zero lower | Θ supplement §4 | L_z/b_+、ε=(4L_z+2)^{-1}、晚正罚 span/晚全零 span 的穷尽二分、单条 z=(r/2)g 及两侧 ±z/2、early cross 负界、ε coefficient 化简均忠实。H₀/余项独立于 calendar；不偷用 P entry positivity。 |
| 463–471，scope | 两份 MD 的模型边界 | Reader-facing 正文明确 zero 仍有 H² drift deficit，且只保存 constant force score。末尾 comment 不增加 controller-family 或 partial-observation 结果。 |

没有把原 M2S v1 的 ordered o(H^{5/2}) 推导改成任意 ξ(H)；新的 Θ(H²) 来自独立累计平衡构造与两分下界。ρ₀≥0、η>0、r>0、held g=±1 和 fixed finite dimension 均保留。

## 3. Score 与完整输入、共同支持与 uniform 范围

Fragment 第 94–95 行明确写 constant scalar shift score，且“不要求 P=I 或恢复 every latent input”；第 341–345 行保留 affine slope loss。因此不会把 partial-mode case 错写成完整创新恢复。第 127–128 行 full record 的 G† 恢复是另一种完整读出实验，不能与 gap 里的单 score 混同。

主稿 revision2 第 351–355 行的 uniform theorem 明示共同 B、Q≻0、紧致所有点严格 Schur gain family、finite k、双向可重复 profiles。Fragment 的 theorem 第 76–77 行仅 fixed A_K/G/B，第 137–143 行 Γ 仅固定 reached-subspace；未引用 thm:uniform，也未宣称 compactness/strict poles 自动控制 singular rank-changing Γ。两者能够同时放入同一稿件，前提是合并时保留这些限制。

“Uniform in the calendar/span” 在 fragment 第 228、400、455 行只指 fixed plant 下的 ∀π 及 common H₀，不是 ∀K。不能把这些词改成 controller-uniform。主稿 SPD 的 β_lo>0/ξ_lo>0 不能迁给 β=0 branch；fragment 未这样做。

## 4. 静态集成检查

实际读取原始 UTF-8 bytes，并独立扫描：

- Fragment 472 行，22 个 unique labels 全以 m2sreg: 开头；与 revision2 主稿 label 集合无交集。
- 唯一外部 ref 为 thm:main，主稿已定义；其余 refs/eqrefs 全在片段内，合并后未解析 refs 为 0。
- TAB=0、孤立 CR=0、其他低控制字节=0；ρ/θ 命令保留为真实反斜杠文本（4 个 `\rho`、14 个 `\theta`），不存在 CR+`ho` 或 TAB+`heta` 损坏。
- 去 comments 后 begin/end environments 正确嵌套、无未闭合，非转义花括号 balance=0 且无负深度。
- 无 documentclass/document environment；所需 amsmath/amssymb/amsthm 与 theorem/proposition environments 都在主稿 preamble。可内联，无新 package 或外部 source 依赖。
- Revision2 主稿本身 TAB/孤立 CR/其他低控制字节均 0；原 label 无重复、内部 refs 无缺失。

这是 source 静态检查，不是编译或 PDF 视觉 PASS。本次未对 fragment 作为 standalone 文档编译，也未创建第二份主稿。

## 5. 合并时需要同步的状态文字和轻微澄清

**状态文字应更新：** revision2 第 30–31 行仍说 stronger zero-penalty rate “still under review”，第 493–494 行仍说 stronger singular regime 为 separate acceptance task。Θ(H²) 已独审接受；内联本片段时，应改为 separately reviewed fixed-controller extension，并保留硬件/有限风险 sweep 尚未完成的实际范围。这两处是版本状态不一致，不是本片段的数学缺口。

两项不阻断接受的表达建议：

1. Fragment 第 123 行的 U_m 可明确为“an orthonormal basis matrix for rangeW_m”。现有 nonredundant rows 的上下文已指 basis；显式写出可避免读者选冗余 columns 后令 UᵀWU 不可逆。
2. 第 351–357 行可直接写 S_t=M_t−n₀，因此 |S_t|≤L+k+2+n₀。现稿“bounded by balance”和 fixed prefix changes constants 在数学上正确，但把两个累计量关系写明更容易核对。

可在 reader-facing scope 末尾再加一句：前文 compact-controller uniform theorem 保持 common Q≻0 的范围，singular-family uniformity 另证。现稿 fixed-plant theorem 已足以隔离范围，此句只是帮助读者避免跨定理误读；不要用它增加新结果。

Revision2 的新增 Kim/Raimondo/Esna/switchback 段与本次已有 primary 阅读边界一致。尤其 Esna2012 两篇保持全文覆盖未审，未因添加 bibliographic entries 写成 theorem-level 排除；fragment 没有新增历史首创措辞。

最终状态：**FRAGMENT MATHEMATICAL/QUANTIFIER CONSISTENCY ACCEPTED；STATIC INTEGRATION PASS；合并状态文字需同步；实际合并稿与 compilation 未由本报告验证。**
