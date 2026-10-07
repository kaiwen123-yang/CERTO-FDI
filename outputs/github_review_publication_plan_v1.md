# CERTO-FDI GitHub 分阶段审查发布方案 v1

2026-10-07。用户已确认替换 **public `kaiwen123-yang/CERTO-FDI`，default branch `main`**；goal暂停，后台400科学runner与metadata publisher继续。本产物只做本地inventory/复制及打包recipe，未改远端、主稿、claims/checkpoint、全局auth/config或进程。root负责旧repo备份及正常commit替换。

## 已实测的发布清单

11:11:00 UTC 的真实400表快照：ZERO74、有效未达目标97、目标PASS55、NOT_RUN174，表SHA与匹配receipt同时捕获。136个已绑定canonical case，共10,219,451,513字节；历史recovery目录4,301,212字节；135→136是后台继续推进，不改称full400完成。current inventory无case复制、无gzip/ADJOINT body读取；大SHA来自既有artifact binding，后续实际打包才核其真实bytes。

Git allowlist约150,167,789原始字节／1205个普通源码与审查文件，另6个已有archive走Release、1个live JSON只走带UTC快照。该体积含历史runtime checkpoint和当前400个冻结direction records，Git对象可去重，不能据此预测最终pack大小。最大已闭合case189,287,596字节；active case单独hold，未来完成后只能在新capture再加入。

源清单为 `work/github_review_publication_inventory_v1.json/.csv`；生成器 `work/github_review_publication_inventory_v1.py`。它把当前Python/PowerShell runtime直接保留为top-level `work/`相对目录，避免只上传文档或把旧runtimeV1伪装成current。真table/receipt snapshot在 `work/github_publication_snapshot_20261007T111100Z/`；SCI producer可能已进一步推进，该时点不会被当成永久“当前”。

## 阶段导航与资产

| 阶段 | Git内容／runtime | Release assets与边界 |
|---|---|---|
| 00 原始研究来源与暂停状态 | source_index、原34项provenance、原稿13tex、审查历史、当前paused-state；原路径/HASH | 原R1ZIP114,986,329B/f703091a…与ADMISSION_REVISION237,126,962B/2b70de94…完整保留；不是第三方下载论文缓存 |
| 01 理论审查 V1/V2 | proofs、11个exact stdlib checks、review、两图source/data/QA、必要版本历史 | V1 780,548B/55e5155c…：无PDF、旧source3490f633…；V2 1,919,557B/6ab32cb8…：R6 source8eaa707…/PDFc8e02b…、11checks+38metadata叶；均非fullD2科学／TACready |
| 02 可运行current runtime | 当前 `work/d2a_core.py/cert_case.py/cert_verify.py/cert_batch.py`、publisher/guard/rebinding/artifact工具、固定protocol0d8b、400directions、mean binding/report、bootstrap与source map；同时保留historical runtimeV1/deltaV2 | R1用原asset恢复；不复制原`work/r1_extract`树、当前locks/PID/controlfiles；current guard/source区别于旧immutable V1 |
| 03 H160真实科学ZIP预演 | 原wrapper、resume/finalize/native cleanup、全部真实错误与新receipts/log、独审 | actualZIP296,443,279B/c5dfadbb…；两个distinctreadout各完整-S一次，avg目标PASS、point有效未达标；原ZIP不含外部恢复源码，Git源码和报告共同交付；full400=false |
| 04 full400未完成时点 | UTC table/receipt、完整row/direction索引、canonical→asset映射、current recipeV3与coverage/IO/cap证据 | 已闭合case全metadata+完整大jets+各自prior/history，计划10个<1GiB资产；old失败/截断按历史scope保留；不复制active/pending case，不颁发finalSCIready |
| 05 当前投稿稿 R8 | current tex/PDF、两图、13-key verified bibliography、contribution/review/compile receipts与R6/R7历史 | R8 source2245714e…/PDF e148cf86…，12页实际CLI编译/layout接受；不同于V2的R6；作者/bios/photos占位、四篇fulltext gap、full400门仍未关 |

`source_index.json`是04:18 UTC的导入provenance，不是全工程inventory；`d2a_source_map_v1.md`的恢复入口／下一步及旧“point仍需扩展”段是历史，保留原bytes，另由stage map导向后续accepted mean与rehearsal证据。不要改写历史或让GitHub导航把partial标成full。

## 源码可运行ROOT与字节合同

新repo保留原结构：`work/`放当前可运行runtime、protocol/directions/mean binding，`outputs/`放mean报告、proof/checks/manuscript/receipts，`references/`放源审查，`inputs/`放index/下载说明，实际原ZIP由Release下载到该精确路径。Python入口以脚本位置推导ROOT，不能只塞在文档目录并声称可运行。保留原 `* -text`属性，避免checkout newline破坏SHA；不改global core.autocrlf。`/work/`目前被ignore，root必须按allowlist显式`git add -f`需要的代码/data，不做全work批量add。

Git的ROOT同时提供136冷case全部稳定小JSON/md/log（排除所有ADJOINT/gz），可直接阅读CASE/receipt/均值/方差及现有certificates，无需先下载10GB。captured CSV/paired receipt在 `work/`原路径可用，`publication_snapshots/`再保留原始UTC capture；`PUBLICATION_SNAPSHOT_STATUS.json`明确这是dated review snapshot、后台producer在别处继续、full400/scientific_ready均false。pending CASE不伪造，完整科学validator仍需匹配witness/R1 assets。

独立读者在新空ROOT下载并核R1原SHA，先运行 `python -S -B -X utf8 work/d2a_extract_r1.py`（拒绝覆盖已有extract），再按asset index安全恢复完整case树，运行 `python -S -B -X utf8 work/d2a_cert_verify.py --case-dir work/<case>`。生成需要已测试Python3.12.10/NumPy2.4.5/SciPy1.17.1；独立verifier为64-bitPython≥3.11 stdlib。复制源码不自动启动batch/publisher；detached launcher是host-locked历史运行入口，其绝对workspace guard需显式review后适配新host，不宣称任意host无改动可launch。

## Git 与 Releases 路线

普通Git会阻止>100MiB单文件，50MiB以上会警告；大二进制适合Releases。因此R1、ADMISSION原稿包、H160科学ZIP和jets都不加入普通Git，small theoryZIP也优先Release便于阶段审查。[GitHub large files官方规则](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

GitHub当前每release最多1000assets、每asset须<2GiB；其about-releases说明无release总大小或bandwidth上限。本方案更保守使用<1GiB，当前cold数据计划10卷，总payload10,223,752,725B，最大组payload1,062,273,438B（另预留4MiB container/manifest）。这是测量与plan，**尚未build/upload，未把平台规则当成吞吐保证**。[GitHub Releases官方规则](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

`work/github_review_publication_prepare_v1.py`默认plan；root可用两个显式local模式：

```text
python -S -B -X utf8 work/github_review_publication_prepare_v1.py
python -S -B -X utf8 work/github_review_publication_prepare_v1.py --stage-code work/github_publication_code_20261007
python -S -B -X utf8 work/github_review_publication_prepare_v1.py --build-cold-assets work/github_publication_assets_20261007
```

模式要求新的指定namespace目录，目标已存在则拒绝。code staging仅allowlist，保留ROOT-relative source，并添加UTC snapshot及case→asset index。cold assets按整个case分组，不丢witness、CASE、CURRENT/prior receipts、projection/direction/covariance/mean或旧attempt；复制前核真实active target、完整tree/stat与已捕获CASE/receipt，stream时核全部SHA/bytes，实际新ZIP再逐member完整SHA/CRC读取，源tree/stat再核。没有science/R1重跑或原data删除。若单个case/history>限额则拒绝，需要单独真实分卷/重组recipe，不能静默裁剪。builder只证明byte packaging，asset namespace仍UNFINISHED400/NO_FRESH_SCIENCE_REPLAY。

原R1/ADMISSION/pair/theoryZIP可直接作为已存在immutable asset上传，避免再物理复制；ROOT应核原HASH/完整upload下载验收。将每个cold actualZIP的真实SHA/size/member receipt写入stage index再发布，不用预测SHA。后续完整400包另需quiescent freeze、完整科学coverage/replay；当前资产不替代那个门。

## 旧repo清理与阶段commit

root先在clone外保存旧repo全部refs/defaultbranch历史的mirror或bundle、验证bundle、记旧main HEAD/URL和备份SHA；检查existingrelease/assets并保留其清单。使用已确认repo的新review branch，从旧main以普通commit删除不相关tracked tree，再依次提交provenance、理论、可运行runtime、H160预演、unfinished快照/assets index、当前R8稿件。经本地allowlist/byte验收后正常push，阶段tag/release供用户逐段比较。保留main历史；不force push、不删repo或默认分支、不擅自改visibility/auth。Root正在该确切HTTPS clone完成这些操作，本agent没有remote mutation。

建议每stage release明确写“theory finite checkpoint”“scoped pair scientific rehearsal”“unfinished400 byte snapshot”“R8 review draft”，并指向该stage commit/manifest/验证范围。背景producer新行应另发新UTC snapshot，不能覆盖本次frozen阶段资产。

## 第三方与交付边界

`work/literature_20261007/`、`work/literature_control_extension/`的完整PDF和全文提取TXT不发布；用已有verified primary URL/DOI/title/edition/locator、citation support matrix和metadata记录。没有未经许可整篇复制，也不把未读版本伪装成已review版本。用户自己的原研究inputs完整source/index/HASH/assets按上表保留；vendor repo不带入，hardware/API协议仅readonly reference文档。

当前root source/metadata inventory是本时点可审查方案，program已实际执行plan但未执行code staging或cold10卷build。本报告JSON绑定inventory/recipe SHA与阶段资产现有HASH；首pass collector曾按generic小文件上限hash22个≤16MiB gzip共326,935,218B（无science、无>16MiB body），历史源/清单已保留；当前collector明确全部gzip/ADJOINT只stat/既有SHA，最新capture无scientific body读入。该事实不写成新scientificPASS。
