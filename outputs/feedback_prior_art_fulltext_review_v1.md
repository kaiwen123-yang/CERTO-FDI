# 反馈／AFD 两篇 2012 近邻：全文追索与定向审查范围 v1

2026-10-07。**结果：L09、L10 的期刊原文或可核对的作者全文均未取得。两篇针对当前 M2 的模型、完整信息权限、feedback 主定理与承重 proof 接口仍为 `UNREVIEWED_FOR_M2`，不得填成“不覆盖 M2”或“全文已审”。** 本轮新增了作者／机构／机器可读题录／本地归档的追索证据；没有关闭原全文缺口。

采用 nature-academic-search 多源检索流程。本报告只新增 `work/literature_feedback2012/` 与本审查文件，未改原15项矩阵、英文稿或台账；未重跑作者算法、旧检查或 D2 扫描。

## 1. 文献身份核对与全文状态

|原矩阵项|经 CrossRef 核对的身份|本次取得内容|PDF/hash/审查页码|M2 定理覆盖判断|
|---|---|---|---|---|
|L09|Alireza Esna Ashari, Ramine Nikoukhah, Stephen L. Campbell, *Effects of feedback on active fault detection*, Automatica **48(5)** (2012), **866–872**, DOI **10.1016/j.automatica.2012.02.020**|作者目录、出版社 introduction/conclusion/section snippets、CrossRef/OpenAlex/Semantic Scholar 元数据、Elsevier XML 题录|`NOT_OBTAINED`；无目标 PDF；无 PDF SHA；无可核定理／proof 页码|`UNREVIEWED_FOR_M2`|
|L10|同三位作者，*Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach*, IEEE TAC **57(10)** (2012), **2532–2544**, DOI **10.1109/TAC.2012.2188430**|作者目录、CrossRef/OpenAlex/Semantic Scholar 元数据及出版社身份入口|`NOT_OBTAINED`；无目标 PDF；无 PDF SHA；无可核定理／proof 页码|`UNREVIEWED_FOR_M2`|

主身份来源为 [L09 CrossRef DOI 记录](https://api.crossref.org/works/10.1016/j.automatica.2012.02.020)、[L10 CrossRef DOI 记录](https://api.crossref.org/works/10.1109/TAC.2012.2188430)，并由 [Esna Ashari 作者出版目录](https://sites.google.com/site/aliesnaashari/publica)及已有 Raimondo 2016 原文 references（PDF 第10页、期刊第116页）交叉核对。

**目录存在一个需避免传播的元数据错误：** [Campbell 的 NCSU 出版目录](https://slc.math.ncsu.edu/RESEARCH/NAAA.html)第187项把 L10 页码写成 592–605，疑似从紧邻上一项复制；CrossRef、Esna Ashari 目录和 Raimondo 原文一致给 2532–2544。本报告使用后者，不将作者目录的错误页码当作另一个版本。

## 2. 实际尝试入口及返回结果

机器请求及响应保存于 `work/literature_feedback2012/`。汇总 `retrieval_manifest_v1.json` 记录 **23次新请求尝试**，其中同时请求的不同源分别计数；网页搜索与工具读取入口另列下表。HTTP 200 仅表示请求成功，不表示取得论文全文。

|入口|本次实际结果及限制|
|---|---|
|[Esna Ashari 出版目录](https://sites.google.com/site/aliesnaashari/publica)|HTTP 200；两篇标题仅链接至 ScienceDirect／IEEE；没有独立作者 PDF。HTML 内 L10 的 `.pdf` 字样位于 IEEE login.jsp 的嵌套目标参数，不是公开 PDF 下载成功。|
|[作者 active-fault-detection 研究页](https://sites.google.com/site/aliesnaashari/research/active-fault-detection)|HTTP 200；研究说明与论文引用链接；仍指向出版社。不能恢复主定理的完整假设。|
|[Campbell 作者主页](https://slc.math.ncsu.edu/)、[publication list](https://slc.math.ncsu.edu/RESEARCH/NAAA.html)|可读；目标条目无全文链接。主页说明可向作者索取副本，本轮未对外联系。目录虽有较早论文 PDF 链接，均非两篇目标。|
|[L09 ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0005109812000714)|可读 introduction、conclusion 和 section snippets；显示机构访问／Purchase PDF。仍未取得完整模型 equations／theorem／proof。|
|[L09 CrossRef 指定的 Elsevier XML TDM 入口](https://api.elsevier.com/content/article/PII:S0005109812000714?httpAccept=text/xml)|HTTP 200，**仅1787字节**；XML 只有 `coredata`，含题名、DOI、PII、刊名、日期、openaccess=false 等；没有 originalText、正文 sections 或 proof。响应节点名 `full-text-retrieval-response` 不能当作已获全文。|
|[L10 IEEE 原始身份页](https://ieeexplore.ieee.org/document/6155074/)|从 CrossRef／作者目录定位；先前明确418的直接全文入口本轮未机械重试。CrossRef 另有 similarity-checking 的 xplorestaging 内部用途链接，没有将它视为授权公开下载入口。|
|[IEEE CSS October 2012 digest](https://ieeecss.org/sites/ieeecss/files/documents/pcd/CSS-Digest-Oct2012.pdf)|搜索定位到论文身份及 PDF 标注；不是目标 article 全文，不从 digest 还原模型／定理。|
|[OpenAlex L09](https://api.openalex.org/works/https://doi.org/10.1016/j.automatica.2012.02.020)、[L10](https://api.openalex.org/works/https://doi.org/10.1109/TAC.2012.2188430)|两项均 HTTP 200、identity 匹配；当前 `oa_status=closed`、`best_oa_location=null`、无 PDF URL。只是该索引的当前记录，不证明世界上不存在公开副本。|
|[Semantic Scholar L09 exact-DOI API](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.automatica.2012.02.020?fields=title,authors,externalIds,openAccessPdf,url)、[L10](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TAC.2012.2188430?fields=title,authors,externalIds,openAccessPdf,url)|两项均 HTTP 200；标题／DOI／作者一致，`openAccessPdf.url` 为空、status=CLOSED。未找到可下载副本。|
|[HAL 官方 search API](https://api.archives-ouvertes.fr/search/)|新尝试为 DOI 两项、精确标题两项、`Feedback in active fault detection` 标题及 `Ashari AND feedback` 广查；全部 HTTP 200、numFound=0。精确原始 q／fl／rows URL 保存于 `metadata_receipt.json`、`hal_title_receipt.json`、`repository_candidate_receipt.json`。没有重试旧 Anubis 受阻的 article 页面或求解其挑战。零检索结果不能作为不存在全文或不存在定理覆盖的证据。|
|[NCSU DSpace author search](https://repository.lib.ncsu.edu/server/api/discover/search/objects?query=Ashari&size=20)、[精确标题 search](https://repository.lib.ncsu.edu/server/api/discover/search/objects?query=%22Effects%20of%20feedback%20on%20active%20fault%20detection%22&size=20)|Python 首次请求有本地 SSL trust 错误；改用 Windows 正常证书验证后 HTTP 200，但实际是 **NC State University Libraries Bot Detection / Anubis** HTML，而非 DSpace JSON。没有解决挑战或继续尝试受控内容。|
|[作者2010博士论文入口](https://theses.fr/2010PEST1060)、`.json`|从论文题名 *Détection active de pannes dans les systèmes dynamiques en boucle fermée* 定位；网页工具失败，Python JSON／Windows landing 请求均25秒 timeout。没有取得该作者 thesis 全文，更不能将可能的早期章节当作2012定稿。|
|[NTNU 公开 CDC2009 目录](https://skoge.folk.ntnu.no/prost/proceedings/cdc09/)、[start.htm](https://skoge.folk.ntnu.no/prost/proceedings/cdc09/start.htm)|公开目录／frame start 可读；其指向 `data/html/nav.htm` 的导航无法取得，未取得 precursor article。站点提示另有密码保护目录，本轮未进入。|
|[2009 IFAC general-cost precursor 的出版社页](https://www.sciencedirect.com/science/article/abs/pii/S1474667016358402)|定位到同作者先行文献；标准 article 页网页工具返回403，未取得可核原文。该篇也不是2012目标定稿。|
|公开精确标题／DOI／作者／filetype:pdf 搜索|多次结合作者、NCSU、INRIA/HAL 和 repository 限域；主要返回上述身份页、相关论文的 references、2010研究活动报告及 request-full-text 页面，没有新的公开目标 PDF。未用二手综述补出原文定理。|

本地范围为：Downloads 当前两份 PDF 做首页身份排除；当前工作区 `literature_20261007`／`literature_control_extension` 与既有 receipts；旧 `C:/Users/ykw/Documents/Codex/2026-10-07` 的研究归档 metadata/index 中检索 DOI／题名，并核 PDF 文件名 inventory。没有找到目标。**这不是全盘所有 archive 解包或所有 PDF 全文扫描；不写“本机不存在”。** 与任务无关的 Downloads 内容未复制到交付物。

## 3. 已知相关性与未审查部分

L09 出版社可读部分讨论：为故障检测添加辅助信号，在线性 feedback 与 bounded uncertainty 下比较输入成本；norm 型最坏成本与一般二次控制成本产生不同解释。它足以说明「反馈影响 active fault detection」和「成本合同影响有用／无用判断」已有原始研究；不足以确定本文 M2 的全信息中性、noise／healthy 共同映射或 sharp calendar 是否已由其某定理直接涵盖。[L09 出版社 introduction 与 section snippets](https://www.sciencedirect.com/science/article/pii/S0005109812000714)

L10 的身份及“quadratic optimization approach”题名已核对，但本轮未读到其系统 equations、允许信息结构、完整 uncertainty budgets、finite/infinite-horizon 定理、算法的最优性条件或承重 proof。**不能从题名、abstract 或 Raimondo 的相关性描述填入其原文 assumptions。** [作者出版目录](https://sites.google.com/site/aliesnaashari/publica)

原15项矩阵绑定的是 raw M0 合同 `outputs/problem_contract_v1.md`，不能作为新的 M2 对照矩阵直接复用结论。此次 M2 已知目标如下；2012两篇各列均仍需全文确认。

|待比维度|当前 M2 的明确合同／承重对象|L09 / L10 原文状态|
|---|---|---|
|feedback 与信息权限|已知固定 K；控制器获得内部 state；诊断器只读 retained full state、不读 fast states／commands；所有原始 fault／health／Q 共同经过同一 dynamics|各自允许 output／state／commands／auxiliary signal 是否读取、反馈是否 hypothesis-dependent：未审|
|完整记录中性|共同可逆 innovation map 使完整 Gaussian composite experiment 与理想 healthy-subtracted oracle 对 K 中性；删除输出后 P_K 改变|是否有对应 experiment equivalence 定理、是否只比较 norm/LQR 成本：未审|
|Gaussian／nuisance|共同 Q≻0；单条完整 scalar healthy path；每侧 rate r/2、free level；差集 rate r，包括 missing nodes|deterministic ellipsoid／bounded uncertainty 与 stochastic Gaussian 噪声的具体位置、两侧预算：未审|
|物理时钟／dead slots|换任务最少 k 个 missing slots；植物、创新、健康持续；无 reset；deterministic calendar|是否允许传感 blackout、transition time、complete-path 同一对手：未审|
|主结果|任意 calendar converse 与 terminal-balanced attainment，D*=C_K H^(5/2)+o(H^(5/2))，growing known fault template|是否有可直接代入同一 sharp loss 及其 matching upper/lower：未审|
|连续 controller 设计|共同固定 SPD Q/B、compact 每点 Schur，bounded k(K)、repeatable exact-k，controller-uniform remainder|是否覆盖这种优化交换、settling 驱动 k 与 profile 类：未审|

因此当前可保留的科学表述是：M2 的待核贡献候选为该具体合同内的 sharp calendar theorem／缺测信息边界，而非“首次考虑反馈”或“首次优化闭环 AFD”。**不得追加“2012论文没有 H^(5/2)／没有 dead slots，所以不覆盖”——尚未取得原文，就没有这样的证据。** 本轮也没有给录用概率或全文新颖性结论。

## 4. 来源绑定与复核入口

|实际使用文件|SHA256|
|---|---|
|`work/literature_feedback2012/retrieval_manifest_v1.json`|`1c9b56b0e256e28dade0383431bd39698a901dfcb863b3aa9ec2be009ea500af`|
|`work/literature_feedback2012/p1_crossref.json`|`09da41d47f8d7069a3208d65dcff78149eb8f129e715572867c98f6bd615161e`|
|`work/literature_feedback2012/p2_crossref.json`|`827d956743eb9c06bdcc1f731ad27edd805d804ec99e3de8f15a41e474bdf286`|
|`work/literature_feedback2012/p1_elsevier_tdm_xml.response`|`9f8e2a0816be2bfa90f3f460b61b0ad66d81c82650a60522d9cc40b7af287c2f`|
|`work/literature_feedback2012/ncsu_author_publications.response`|`260dae4174488250b1e0a58f1d9b7fc593bb15d310c8e16f07138f700528deaa`|
|`work/literature_feedback2012/ashari_publications.response`|`53958de5adadc6f7be71b9b86517c7fcb0f65c2315e8b74974d73a034375c2c9`|
|`outputs/novelty_matrix.csv`|`d34f2e7a98e47973b46d8288caad9bb82c82f652f8ae0719de5c1311dfc9306d`|
|`outputs/m2_problem_contract_v1.md`|`794c245d0fdb672021cb36566382d68834b2abe20331dde0bc01a0bc71671eae`|
|`outputs/m2_controlled_memory_theorem_v1.md`|`38d2aecf2d00a6a781f0a99f6448d93a4d2fcccd1e895526ca3c5fed2c3455b1`|
|`outputs/compact_controller_uniform_bridge_v1.md`|`89762501f1272eb8b0ed5150985225655e62f0681d24c62c41729750dbcdf351`|
|`work/literature_control_extension/raimondo_automatica2016.pdf`（仅参考文献定位，不在此复审其 theorem）|`cf26542d1749811684b7a77123883aa399b59c31d9f7a4f2ea199a6528a8df84`|

manifest 内另绑定全部新脚本／responses／receipts 的 bytes 与 SHA，记录错误／HTTP 状态和精确 URLs。其 `pdf=null`、`pdf_sha256=null`、`audited_pages=[]` 是有意保留的真实缺口，不是漏填。

**验收状态：身份／检索收据完成；L09/L10 全文定理审查未完成，原因是未取得合法可读完整来源。不能获取不等于没有覆盖；此次结果不能替代这两篇的模型与证明核查。**
