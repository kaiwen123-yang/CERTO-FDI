# GitHub发布限定独审 v1

2026-10-07。审查对象为 `kaiwen123-yang/CERTO-FDI` 的初始发布 `9195f7124e56040a79fc0751bbf9b5fd87d30360`、导航修订 `7d7f32e8fd5b76b90a83cd7b947cd11fee7442c7` 和其发布lineage补充 `842d1e0de994dc5ad02b30b2c9b12bef8895f4b5`；三者均已有真实远端main核对。**代码、科学范围与导航/lineage修订通过只读核查，无尚需修复的代码或文档问题；资产上传尚在进行，不能据此宣告19项发布全部验收。** 初轮发现与修订分开保存，未将旧SHA静默改成新状态。

本轮使用已认证 `gh` API读取main、branches、tags、Release小元数据；读取独立HTTPS clone中的文本/JSON/两个冻结CSV及小文件hash。未执行科学、R1、旧fixtures、编译、硬件或remote mutation，未下载/hash大资产、重复制大数据或触碰已停止的任务。实际网络资产检查是metadata，不是科学算术验收。

## 1. 已验证的发布边界

- 初始remote main与独立clone同为 `9195f7…`；导航修订后两者同为 `7d7f32…`，lineage补充后同为 `842d1e…`，clone clean。remote只剩main分支，11个 `legacy-pre-theory-20261007/*` annotated tag存在；4个实际Release均为非draft prerelease。本轮只核refs/metadata，不重新验证legacy大bundle内容。
- 初轮README、Guide、StageIndex、Release页面共144个实际本地相对链接均存在；842d复核147个相对链接也均存在。index的104条角色记录（99个distinct小artifact）全部SHA匹配。并没有发现真实Markdown相对ZIP链接断裂：大ZIP移到Release是设计，未放回main。初轮的具体问题是三个Release入口仍null和发布前状态仍在，现由7d修订补齐实际tag/asset地址且明确上传另行追踪。
- R8 source/PDF、mean/physical/proof范围、13条书目与4全文缺口、R6 V2不含R8、PiPER仅静态准备、`full400=false`/`scientific_ready=false`均保留。H160原2d wrapper失败、eaa恢复后长路径错误、native修复及外部finalizer源码/新receipt入口都在main，原ZIP不含这些外部恢复源的限制也明示。
- 原 `publication/FINAL_GIT_PAYLOAD_MANIFEST.json` 记录的2799源文件验证及6个editorial/final-stop overrides属于已有发布记录；本审查没有再hash全部200MB或重做该源验证。

## 2. 初轮发现及7d修复

| 发现 | 初轮准确位置/证据 | 已推送修复 |
|---|---|---|
| checkpoint身份指针失配 | `outputs/STAGE_INDEX_v1.json`的`snapshot_source.path=research/checkpoint.json`声称SHA `1af609cb972aee478116d8e9f084c11794bb0963c61ed273582c04cc3ae40920`；该HEAD文件已是停止版SHA `a19b48400291bce02654199a6dd9a24c2fc4d530ee3861746548a44aef8bc088` | 原实字节从本地预发布capture保存到`publication_snapshots/stage_index_basis_20261007T105314Z/research/checkpoint.json`，指针转向该文件，保留原SHA和原时间；没有改旧SHA冒充停止状态 |
| Release迁移入口未更新 | JSON的3个`release_assets.href=null`、`publication_status=LOCAL_NAVIGATION_PREPARED_REMOTE_ACTIONS_NOT_PERFORMED`；ZIP不在main | `publication_status`改为main已发布/资产上传进行中，3个entry有实际tag页与asset下载地址，上传/remote digest单独追踪；不声称已全部完成 |
| 11:11与最终停止表混写 | README旧代码数据段把root CSV概括为11:11同一次capture；实际root CSV为最终停止版本 | README明确原11:11基线及最终停止；StageIndex追加原CP依据/最新stop入口与`source_manifest_scope`，不改scientific artifact |

原CP的可审阅实字节来源是本地 `work/github_publication_code_20261007/research/checkpoint.json`，10,913 bytes，实际SHA正是 `1af609…`；现在发布的专门快照保持同值。此来源只作为本轮复制出处，不要求读者访问本机路径。

7d实际diff恰为README一段、StageIndex JSON的publication/path/href/hash/边界字段、StageIndex MD附加发布说明及一个原CP快照文件。没有修改科学源码、主稿、风险数据或证明。原导航md的旧SHA与新index-md SHA `9bd5257c65a0e381ff20e8d69e3a59a5266ca3aac73c0bbeb8b5d284b93d92c8`应分别解释为原导航与publisher修订，不能互相替换。

## 3. 两个时点与manifest的含义

| 范围 | CSV SHA | 分类 | canonical case |
|---|---|---|---:|
| 11:11历史snapshot | `348d384f13350151887ae92c6a14693fb6dbcedae853067cdcfd8c3919aecf47` | 74 ZERO、97有效未达、55达标、174 NOT_RUN | 136 |
| 最终停止/root表 | `2d6eb3f0beba4be3ff1040a3bb5d3d24785e8fcb23610c67f2af169bfcd7a5fa` | 74 ZERO、98有效未达、57达标、171 NOT_RUN | 139 |

两个CSV都为400行。原表在`publication_snapshots/github_publication_snapshot_20261007T111100Z/work/`保持；最终表在`publication_snapshots/final_stop_20261007/work/`及可运行root `work/`，actual hashes分别匹配。最终3个新case与asset011补充记录分开；取消point仍NOT_RUN，不能回填FAIL/PASS。当前139case/171未算不是full400闭合或新全量科学replay。

`PUBLICATION_SOURCE_MANIFEST.json`是11:11原基线，旧asset index也是136case；它们不应被当作当前HEAD所有root文件的单一hash清单。`GITHUB_FINAL_STOP_SUPPLEMENT_MANIFEST.json`、最新stop和已存在的6-overrides Git记录解释停止覆盖。7d已在README/Index明示这一点。

**发布lineage建议已由842d闭合：** `publication/FINAL_GIT_PAYLOAD_MANIFEST.json`是9195发布阶段的文件hash记录，7d又变更README/StageIndex两文件并新增CP快照；该旧记录不会自动覆盖新增导航修订。842d保留旧manifest字节，新增`publication/DOC_PATCH_RECEIPT_20261007.json`记录base9195、明确的`reviewed_patch_commit=7d…`、4个path的旧/新SHA及专门CP复制SHA，README另加该补充入口。receipt字段按其明确的7d时点核对；842d自身只是receipt及README新增链接，不冒称旧全文件manifest覆盖后来所有HEAD。没有重hash200MB或重新科学验证。

## 4. 远端资产状态与最终门

初轮实际API快照 **2026-10-07T12:11:08.562894Z** 有5/19 uploaded；后续实际API快照 **2026-10-07T12:23:55.595566Z** 有9/19，新增H160与cold001–003。九项name/size/server `sha256` digest均匹配manifest；其余10项正由publisher上传。4个prerelease对象真实存在，缺项按进行中记录，不当作上传失败，也不伪造全部verified。完整API字段/asset ID及pending清单见本报告JSON；资产阶段依据独立时间快照，不与已接受的842d代码/文档阶段混为同一完成声明。

最终资产发布关闭条件应由publisher的新实际receipt满足：19个expected `(release_tag,name)` 全集、`state=uploaded`、实际size、server digest与manifest一致；若digest缺失，必须保留`remote_digest_unavailable`，不能声称同等hash验收。使用API实际`browser_download_url`补入口；不要因tag页已创建就假设每个asset链接已可下载。无需由本审查再次下载大包。

代码审查与上传完成是分开的阶段。上传完成及本次doc lineage补充不会改变full400未完成、四全文缺口、非线性/mean有限范围或TAC not-ready，也不能新增任何科研成功声明。
