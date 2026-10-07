# 本地 Zotero：两篇反馈／AFD 2012 原文只读检索 v1

2026-10-07。**结果：在本次确认的 Zotero 当前库、两个现有备份库、storage 目标文件名和旧控制文献 metadata 索引中，未匹配到两篇目标的元数据或 PDF 附件。没有复制论文，也没有新增原文模型／定理审查；L09/L10 对 M2 的覆盖仍为 `UNREVIEWED_FOR_M2`。** 本地未命中不证明用户其他库、未同步附件、generic 文件名 PDF 或其他归档中不存在目标。

目标为：

- *Effects of feedback on active fault detection*, Esna Ashari / Nikoukhah / Campbell, Automatica48(5) (2012), 866–872，DOI `10.1016/j.automatica.2012.02.020`。
- *Active Robust Fault Detection in Closed-Loop Systems: Quadratic Optimization Approach*, 同作者，IEEE TAC57(10) (2012), 2532–2544，DOI `10.1109/TAC.2012.2188430`。

## 1. 本次实查范围

现有工具清单没有可调用的 Zotero connector。先尝试现有本地 connector `http://127.0.0.1:23119/connector/ping`；结果为 ConnectionRefusedError 10061，未启动 Zotero、未更改服务器设置，也未执行后续 items API 请求。此前记忆中的 API-v3／user-library-ID 仅作检索线索，没有把旧 ID 或旧 collection 数量当成本次在线确认。

`C:/Users/ykw/Zotero/` 确实存在。实际读取 `AppData/Roaming/Zotero/Zotero/profiles.ini` 的 default profile，以及 `Profiles/37r7949a.default/prefs.js` 的 dataDir／useDataDir 两项；当前配置再次确认 dataDir 为 `C:/Users/ykw/Zotero`，useDataDir=true。

只读查询以下三个已存在文件：

|数据库|查询方式|目标 DOI／title／author／attachment 命中|
|---|---|---|
|`C:/Users/ykw/Zotero/zotero.sqlite`|`file:///C:/Users/ykw/Zotero/zotero.sqlite?mode=ro`|0|
|`C:/Users/ykw/Zotero/zotero.sqlite.bak`|相同 URI `mode=ro`|0|
|`C:/Users/ykw/Zotero/zotero.sqlite.1.bak`|相同 URI `mode=ro`|0|

sqlite3 连接均使用 `uri=True` 和 `PRAGMA query_only=ON`，只读取现有 schema 与目标元数据查询。没有修改／解锁／修复 DB，没有复制 DB，没有打开写连接。

此外只检查 `C:/Users/ykw/Zotero/storage` 中 **358个 PDF 文件名**，筛选 Ashari、Effects…feedback、Active…robust…fault、两个 DOI 片段等目标标识；匹配0。没有读取这358份 PDF 的正文，也没有复制无关文献。

旧控制文献工作区 `C:/Users/ykw/Documents/Codex/2026-10-04/2026-9-25-10-2-5/work` 中，以 `*zotero*.json`、`*catalog*.json`、`*metadata*.json`、`.bib`、`.ris` 范围限定的 **56份现有索引／metadata 文件**，按两篇 DOI、精确题名及 Esna Ashari 检索，命中文件0。没有把旧 snapshot 当作当前库；该查询仅作额外历史线索核对。

## 2. 查询条件与完整性边界

三份 DB 均执行以下8组定向查询，详细 SQL 保存于 `work/literature_feedback2012_zotero/query_sqlite_readonly.py`：

1. DOI 字段忽略大小写匹配 L09 DOI。
2. DOI 字段忽略大小写匹配 L10 DOI。
3. title 的 Effects / feedback / active / fault / detection 完整次序匹配，允许标题前缀、空格和标点变化。
4. title 的 Active / robust / fault / detection / closed / loop / quadratic / optimization 完整次序匹配。
5. 关联 item creator 中 Esna / Alireza / Ashari 组合匹配。
6. 关联 item creator 的 Ashari 姓氏宽匹配，避免只漏掉缩写名字。
7. 全部关联 itemData 字段中查询两篇 DOI，覆盖 DOI 写在 extra／URL 等字段的情形。
8. itemAttachments 的 title 查询目标，包含 standalone attachment，不要求先命中一个 parent item。

查询没有按 collection 或 user-library-ID 过滤，也没有排除 deletedItems，因而不只检查一个控制文献 collection 或仍在当前视图的正常条目。所有8组在三个 DB 中均0匹配，没有可供进一步定位的 item key／parent item／attachment path。

**仍未覆盖：** generic 文件名且没有可匹配 Zotero 元数据的未挂接 PDF、PDF 正文藏有目标而 metadata 被错误录入的文件、未同步／远端附件、其他未被当前 profile 指定的数据库，以及未列出的用户目录。没有对这些范围作不存在判断。没有重新尝试先前23个失败 URLs，没有付费、对外联系或操作 user library。

## 3. 只读凭据与来源哈希

每次 DB 连接前后记录 size／mtime_ns 及对应 `-wal`、`-shm`、`-journal` 的存在性。三份 DB 的这些文件元数据前后一致，所有所查 sidecar 前后均不存在；receipt 中 `file_metadata_unchanged=true`。这项核对与 URI `mode=ro` 的读取方式分别记录，不冒称已在读取前后做两次全文件 SHA 比较。

|实际来源／收据|SHA256|
|---|---|
|`C:/Users/ykw/Zotero/zotero.sqlite`|`6ca8e8af2376567fc855b9f611c4e74b7c8fcd1892f4f56af0abe608bda7902a`|
|`C:/Users/ykw/Zotero/zotero.sqlite.bak`|`17fdf3cf74cb3936c2cd0f0f78cf0e47f9d95ba85915b9f532ddacfd7963f4bf`|
|`C:/Users/ykw/Zotero/zotero.sqlite.1.bak`|`0ba490f5337de65569b2b20ed8e0f455fe551316a2eaf00ed1a7ae05257f17a2`|
|`work/literature_feedback2012_zotero/sqlite_readonly_lookup.json`|`a13f6bdd1d0f6268082d5a30aab83bb6a4f90957474c036738c9a0180a8dd6a5`|
|`work/literature_feedback2012_zotero/sqlite_readonly_zotero_sqlite_bak.json`|`9442b3fa1adaa49cd3d990b60254c88e12441657d5d23a21741af43af85bda73`|
|`work/literature_feedback2012_zotero/sqlite_readonly_zotero_sqlite_1_bak.json`|`6ed438b62b300676d362c757890c2dae1b14bc26f11086335d146fb3caca9eda`|
|`work/literature_feedback2012_zotero/local_api_lookup.json`|`7174a88772a1cb4dbc1289c4a354dce5e63e8d7bcb233304bc63702cdf353ae7`|
|`work/literature_feedback2012_zotero/filesystem_lookup.json`|`5dc235191ffe53c400ba19d4310655f2a71d6e95742a5f2ab473bef75595199e`|
|`work/literature_feedback2012_zotero/query_sqlite_readonly.py`|`6da70f37d91ea3d838642ce329baa7bae5842405176cb33dba4ccc7fe4976a2e`|

以上哈希另保存于 `source_hashes.json`；只保存目标查询的空结果、schema 和范围收据，没有导出整个用户 metadata library。

**验收结论：本地只读目标检索完成，未获得目标全文；两篇2012原文的 M2 定向证明审查仍未完成。** 仅新增本报告及 `work/literature_feedback2012_zotero/`，未改旧 lookup、novelty matrix、稿件或 ledger。
