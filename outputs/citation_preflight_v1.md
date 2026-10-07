# TAC 工作稿：有限来源引文预检 v1

2026-10-07。**书目与 cite-key 基础检查通过；13 条可用书目中，11 条有既有 primary 全文与定向支持定位，2 条仅完成身份／主题核对。四个全文比较缺口仍然开放，不能据本轮宣布穷尽历史新颖性或排除覆盖。**

本轮严格绑定 `certo_fdi_control_memory_draft_v1.tex` revision 4，SHA256 `70dc68db61599470cb6cd82ff6a2f83bcd30cdd4db89675e8074eab4e146f302`。仅写本报告、`submission_bibliography_verified_v1.tex` 和 `citation_support_matrix_v1.json`；没有修改主稿、ledger、原15项 `novelty_matrix.csv` 或既有文献缓存。所有定位采用实际缓存 PDF 页码；印刷页码仅用于已经取得的出版排版／会议全文。

## 1. 本地书目卫生

按 citation-verifier 技能先运行本地扫描，并单独解析 `\cite`／`\bibitem`：当前基线有 **10 个 cite 命令、11 次 key 出现、10 个唯一 key、10 条书目**；未定义 key、重复书目 key、引文占位项均为0。扫描器的 `bib_keys: 0` 只是未发现 BibTeX `.bib` 项，不代表手写 `thebibliography` 没有条目。

全部原10个 key 在建议 fragment 中保持不变。新增 `switchcost`、`multipleplays`、`ossenkopf` 均对应已经取得并定向读过的 primary 全文。fragment 共13条；单独 fragment 不是独立 LaTeX 文档，没有用它假装完成整稿编译或 IEEE 页数验收。最终装配应按正文实际首引顺序排列。

## 2. 书目信息与版本处理

| 条目 | 核对／清理结果 | 可核位置与版本 |
|---|---|---|
| `controlled` | 题名、3位作者、TAC58(10)、2451–2464、2013、DOI `10.1109/TAC.2013.2261188`一致 | 作者站点的出版排版全文首页；§II–III，PDF pp.2–5／印刷 pp.2452–2455，Proposition1、Theorems1–2 |
| `markov` | 保留已读 arXiv v2；年份2014正确；链接固定到v2 | [官方v2记录](https://arxiv.org/abs/1310.1844v2)，2014-06-28；§3 PDF pp.6–7，Theorems4.1–4.2 pp.8–10、5.1 p.11 |
| `zonotope` | 补 issue6及 DOI `10.1016/j.automatica.2014.03.016`；作者、50:1580–1589、2014一致 | 作者缓存全文首页 DOI；[出版身份页](https://www.sciencedirect.com/science/article/pii/S0005109814001083)；§2、§3.2、Theorem3、§5，PDF pp.2–5／1581–1584 |
| `convex` | 官方注册题名用单数 **Hypothesis**；PDF首页用 **Hypotheses**。保留官方书目题名并记录变体，不强行当作两个作品 | [官方v7记录](https://arxiv.org/abs/1311.6765v7)，2016-02-23；PDF首页2016-02-24；§2.1–2.3.1、Theorem2.1，PDF pp.3–6，Gaussian最近对式(7)及解释在p.6 |
| `allan` | 保留已读 arXiv v1／2001；补明确v1链接 | [官方v1记录](https://arxiv.org/abs/astro-ph/0105071v1)，2001-05-04；§4.1，缓存 PDF pp.5–7，(15)–(17) |
| `kim` | DOI补为 `10.23919/ECC.2013.6669785`；全文6页，完整书目页码 **1940–1945**，不能将旧定向阅读1940–1944误当文章页码 | 原会议全文首页有ECC、2013-07-17–19、Zürich及1940；[IEEE deposited metadata](https://api.crossref.org/works/10.23919/ECC.2013.6669785)核对DOI及末页。§V-C，PDF pp.4–6／1943–1945，(20)–(25)，Remark3在p.5／1944 |
| `closedset` | 题名、4位作者、Automatica74:107–117、2016及DOI一致 | 作者缓存出版排版全文首页；§2.2 p.3／109，Theorem1 p.4／110，Lemma3、Theorems4–5、Algorithm1 p.5／111及appendix pp.9–10／115–116 |
| `feedback2012` | Automatica48(**5**):866–872、2012、3位作者及DOI一致；补issue5 | 原有出版社／作者目录／publisher-deposited metadata收据；**article full text未取得，无定理页码** |
| `robustfeedback2012` | TAC57(10):2532–2544、2012及DOI一致；不传播Campbell目录中的错误页码592–605 | 原有作者目录及publisher-deposited metadata收据；**article full text未取得，无定理页码** |
| `switchback` | 保留已读 v4／2025，不替换为另一出版版本；2020是v1初次提交年 | [官方v4记录](https://arxiv.org/abs/2009.00148v4)，2025-09-17；Assumptions1–3 pp.6–7、12，Theorem2 p.13，相关proof pp.56–57 |
| 新增 `switchcost` | Vaidhiyan／Sundaresan；arXiv1505.02358v1／2015 | [官方v1记录](https://arxiv.org/abs/1505.02358v1)，2015-05-10；§II-A/B pp.2–4、Proposition5、Theorem6 |
| 新增 `multipleplays` | Lambez／Cohen；arXiv2108.03082v1／2021 | [官方v1记录](https://arxiv.org/abs/2108.03082v1)，2021-08-06；§II pp.4–5，§III-C Theorem1 p.12 |
| 新增 `ossenkopf` | Ossenkopf；引用实际读过的 arXiv0712.4335v1／**2007** | [官方v1记录](https://arxiv.org/abs/0712.4335v1)，2007-12-28；§5，缓存 PDF pp.10–11，(23)–(27) |

预印本中未填期刊卷／页码，是版本身份的有意保留。GJN的官方记录另列EJS9(2):1645–1712 (2015)，Schieder和Ossenkopf的记录另列A&A相关DOI，Lambez–Cohen另列TSP相关DOI；这些出版信息**没有被合并成声称已读过的publisher edition**。需要改引出版版本时，先核当前承重 result／locator与其版本差异。

Ossenkopf缓存PDF的生成页眉为2021-01-12，这不是论文首次发表年。Schieder官方记录comments称11页，实际缓存PDF为12页；报告与矩阵采用实际缓存定位，不借metadata page count改写页码。GJN官方metadata写A. Juditski，缓存全文写Anatoli Juditsky；fragment采用全文拼写。Markov官方metadata及其PDF写Venupogal，而TAC2013全文写Venugopal；fragment的V. V. initials不受该变体影响。

## 3. 引用实际能支持什么

当前11次引用的支持关系记录在JSON中，逐条绑定 revision4 行号、实际PDF hash、精确locator与限制。结论是**现有相关工作陈述在声明的范围内有支撑**，但以下边界必须保留：

- `controlled`／`markov`支持已知观测律下的控制感知、Markov与序贯成本前史；不能把finite fully observed Markov合同直接代入当前两条完整漂移路径、growing fault和真实state blackout。
- `zonotope`／`closedset`支持history-aware集合诊断和闭环moving-horizon输入设计。不能说既有方法忽略全史coupling、全部open-loop或每块遗忘旧测量。Raimondo中conservative observer只有sufficient implication；converse需exact observer。
- `convex`确实在PDF p.6给最近Gaussian mean pair和affine detector，相关原设置为compact convex mean sets。稿中的unbounded healthy level经closed-polyhedral image取得最近对，以及asymmetric uniform-power threshold，由稿件自己的论证处理；不能声称是原文某个相同一般性定理的逐字套用。
- `kim`足以否定“反馈传播Gaussian均值与covariance”“闭环统计主动诊断”首创表述。Remark3要求gain单独设计，Algorithm1不能直接完成对`(K_t,nu_t)`的完整joint global optimization；其结论描述local input optima。
- `allan`／`ossenkopf`支持实际dead time、stochastic drift及对称补漂移优化的前史。区别应落在当前complete-path deterministic rate adversary、Gaussian information deficit、任意calendar converse和匹配系数，不能说旧观测设计没有physical dead time。
- `switchcost`的Theorem6保留先error limit、再sluggish参数趋零的顺序；`multipleplays`的Theorem1保留known iid f/g、sequential Bayes objective和`s=O(c)`。这些additive switching charges不等同于当前至少k个排除状态读数的植物／健康路径持续演化。
- `switchback`支持fixed-horizon randomized minimax scheduling与known carryover。不能把所有randomization points都当作真实switch，不能据统计目标不同作穷尽优先权排除。
- 两篇Esna2012在当前稿只作**身份与研究主题**承认，并明确标注全文覆盖未审；不把publisher snippets、digest或abstract变成theorem。

适合装配的两处最小正文补充为：

```latex
Switching charges in sequential active search are also established
\cite{switchcost,multipleplays}. These known-law sequential risk contracts
differ from the present exclusion of plant-state readings while dynamics
and a complete healthy path continue on the physical input clock.

Symmetric reference--source--source--reference phases and timing optimized
against instrumental dead time are explicitly treated in
\cite{ossenkopf}.
```

可以把第二处合并到原`allan`段并用`\cite{allan,ossenkopf}`。JSON不把新增key当作已存在于revision4正文；它们是供装配选择的已读近邻。

## 4. 四个未关闭的全文缺口

| 文献 | 已确认身份 | 尚缺最小证据 |
|---|---|---|
| Esna Ashari／Nikoukhah／Campbell，*Effects of feedback on active fault detection* | Automatica48(5), 866–872, 2012；DOI10.1016/j.automatica.2012.02.020 | 可读完整article；模型、信息权限、完整主定理／proof对当前M2逐项比较 |
| 同作者，*Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach* | TAC57(10), 2532–2544, 2012；DOI10.1109/TAC.2012.2188430 | 同上；digest／题名不能代替article full text |
| Cheng／Steinberg，*Trend robust two-level factorial designs* | Biometrika78(2), 325–336, 1991；DOI10.1093/biomet/78.2.325 | 完整trend／AR(1)合同及承重定理；摘要已不支持“只有polynomial trend”的概括 |
| Coster／Cheng，*Minimum Cost Trend-Free Run Orders of Fractional Factorial Designs* | Annals of Statistics16, 1188–1205, 1988；DOI10.1214/aos/1176350955 | 完整minimum-cost／trend-free run-order模型、结果及与当前calendar合同的定向比较 |

本轮没有重新机械请求先前23个失败全文入口、没有启动Zotero、购买文献、联系作者或新增理论。现有 `feedback_prior_art_fulltext_review_v1.md` 和 `feedback_local_library_lookup_v1.md` 的“未取得／未命中”结论保持原范围：不能获取不等于没有覆盖，本地检索未命中不等于本机所有归档都不存在全文。

原15项matrix绑定M0；本轮JSON只保留Cheng／Coster身份与原缺口，不把旧M0排除结论升级为M2。`novelty_control_memory_collision_v1.md`的文献缓存／定向结果可复用，但其当时稿件hash不是revision4；本轮没有把它重新包装成对当前所有M2S／uniform-controller结果的独立历史优先权认证。

## 5. 交付与最小后续

- `submission_bibliography_verified_v1.tex`：13条IEEE-style手写书目fragment，保留版本身份及source locator注释，SHA256 `cf0ce385edee79785471d656f4113dd32fd0c88d3ea8e1f5fae174e2cf67671a`。
- `citation_support_matrix_v1.json`：13条书目支持与2条未引全文缺口；含baseline binding、PDF hashes、metadata来源、cite行号、allowed／unsupported范围和静态验收。

**最小后续是把新增3条与具体supported正文比较一致装配、保持四个全文缺口具名、在获得原文并完成定理接口核对前避免历史排除语句。** 未解决全文比较不阻止本轮形成可复核书目包，但本包不颁发“历史首次／穷尽新颖性通过”的结论。
