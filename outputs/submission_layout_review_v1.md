# IEEE layout candidate review v1

日期：2026-10-07。本次只新写 `outputs/submission_layout_candidate_v1.tex` 和本报告 `.md/.json`；根主稿、冻结 body fragment、证明、ledger均未改。中间脚本、编译日志/PDF/PNG在 `work/`。使用 latex-compile 与 PDF 技能；没有安装runtime、重跑旧数学checks或D2。

**有限验收：候选实际第二轮CLI编译 exit 0，10页；末次完整TeX log Overfull=0，undefined ref/cite=0，missing character=0；全部10页115dpi逐页视觉读取未发现越栏、交叠、公式裁切、编号碰撞或表格cell碰撞。** 这不等于投稿就绪、数学新增验收或所有编译warning消失。

## 1. 字节绑定

|对象|SHA256|
|---|---|
|根revision5 baseline|`e5d3c2d639e828795518101a78ea08cec56ea8bb1b44a01282186180fc75a371`|
|layout candidate|`d1ba94f30430e9ec9c36b2063296231c518204d17812ac61e8a014691ac16cb4`|
|末次实际PDF|`883551b42d2707775fc5c955f0ddc35396f0adf39e6efa3c06a75323d8f7bd02`|

末次PDF：`C:\Users\ykw\Documents\ChatGPT\CEO-FDI\work\latex_build_turn2\layout_candidate\round2\submission_layout_candidate_v1.pdf`。10页包括现有正文、唯一既有解析图、全部附录和13项references；真实作者metadata/bios/photos仍未提供，不能凭此页数虚构包含这些内容的最终页数。

## 2. 实际诊断与修复

基线已成功编译但多个display侵入中缝/右栏。实际读取基线p2/p8/p10并结合根的观察；问题不是数学失效，而是单栏长式无换行。先一次改35处display为equation内aligned或多行unnumbered aligned；长chain按项/关系分行，单一公式编号和label保持。候选round1成功、11页，完整日志只余H120四列表的93.59007pt overfull，但确认TU/ptm缺失导致实际Latin Modern fallback。

根据根新增授权，round2加入标准 `\usepackage[T1]{fontenc}`，不改journal class、geometry、字号或数学包。H120表按完整词语换行header/readout并设4pt列间距；六个数字cell顺序、数值与单位表达全部保持。round2成功、10页，所有overfull消失。未为了页数删证明/假设/限制，未用tiny、scriptsize或resizebox。

另按根已认可审查补两处文字：`Throughout, $a_j^h=\mathbf1_{\{h=1\}}a_j$.`；switching penalty明确为 `$s=O(c)$ as delay cost $c$ tends to zero`。这两项是事先授权的定义/已审scaling措辞，区别于布局-only公式比较。

## 3. 数学保全核验

35处变化逐式对比ordered semantic tokens，仅忽略空白、quad/qquad等spacing、alignment ampersand/row breaks、display/align/split/aligned环境及label/notag等布局命令；每处token顺序和数字顺序完全相同。表内六个mathcell直接逐项相等。反向撤销所有记录的layout、fontenc、两处授权clarification和table排版后，候选全文恢复到基线原文（换行统一为读取时LF）；因此没有未记录的prose、proof、quantifier或数学变更。48 labels和13 bibkeys顺序不变。

|基线行|公式或布局标识|语义token顺序|数字顺序|
|---|---|---|---|
|95|`sf:plant`|相同|相同|
|115|`sf:path`|相同|相同|
|130|`sf:predictor`|相同|相同|
|136|`sf:interval`|相同|相同|
|150|`sf:information`|相同|相同|
|171|`sf:penalty`|相同|相同|
|176|`sf:positive`|相同|相同|
|181|`sf:upper`|相同|相同|
|217|`sf:capacity-bound`|相同|相同|
|255|`nearest-pair separation`|相同|相同|
|283|`common-matrix example`|相同|相同|
|293|`matrix gap penalties`|相同|相同|
|303|`scalar finite sums`|相同|相同|
|320|`plateau candidate set`|相同|相同|
|326|`near-unit limit`|相同|相同|
|469|`nonlinear threshold and gap`|相同|相同|
|571|`sf:gamma`|相同|相同|
|617|`sf:affine`|相同|相同|
|640|`sf:support`|相同|相同|
|660|`sf:dual`|相同|相同|
|721|`macro inequality`|相同|相同|
|749|`sf:block`|相同|相同|
|761|`packed block asymptotics`|相同|相同|
|773|`local dual levels`|相同|相同|
|803|`observable repair definitions`|相同|相同|
|816|`observable repair bounds`|相同|相同|
|833|`sf:positive-support`|相同|相同|
|847|`repair energy`|相同|相同|
|853|`exact two-gap loss`|相同|相同|
|902|`sf:slope-loss`|相同|相同|
|942|`zero-penalty length and positive tail`|相同|相同|
|957|`sf:zero-positive-case`|相同|相同|
|968|`complete zero-case path`|相同|相同|
|975|`late constant-score cross`|相同|相同|
|997|`sf:zero-preserved-case`|相同|相同|

原IEEE/amsthm环境配置、所有proof起止和root已有的leavevmode/局部textit段头保持。源内已无proof紧接sectioning `\paragraph` 的旧触发，未重新引入missing-item错误。参考文献字体未出现proof作用域泄漏。

## 4. 编译与视觉证据

编译沿用plugin `build_tectonic_command`的实际Tectonic 0.17.0命令，增加 `--keep-logs --keep-intermediates`。两轮JSON均使用实际 `exitCode/log/pdfPath` schema；完整stdout另保存而非仅靠截尾字段计warning。

- round1: `work/layout_compile_round1.json` / `.stdout.log`，11页、成功，剩table overfull。
- round2: `work/layout_compile_round2.json` / `.stdout.log`，10页、成功。
- 末次完整log：`work/latex_build_turn2/layout_candidate/round2/submission_layout_candidate_v1.log`。
- 末次所有PNG：`work/latex_render_turn2/layout_candidate/round2/page-01.png` 至 `page-10.png`；已逐页实际读取。

末次full log还有6个Underfull hbox提示；对应文字正常阅读，不构成侵入或裁切。全PDF字符水平边界为约48.96至563.05pt，正常margin内；这项几何检查补充而不代替逐页视觉读取。图在figure*中，textwidth使用合法，两列下方文本没有覆盖图注。H120表、main theorem、SVD/Gamma、support cases、positive macro inequality、weighted repair、zero两case及reference页面都实际检查。

## 5. 字体的实际边界

Round1基线/候选的正文实际LMRoman10-Regular和bib LMRoman8-Regular；这说明TU/ptm缺失后的fallback，不能只从log bx/it/sc字样推断正文泄漏。Round2实际PDF标题、正文、theorem/venue italic等使用NimbusRomNo9L-Regu/Medi/ReguItal，属于IEEE类ptm指定的Times兼容文本族；数学继续Computer Modern，图自有Arial/DejaVu字体沿用既有图。p10 reference主要Regular，emph venue才Italic。pypdf实际检查全部24个font descriptor/stream，含Type0 descendant和图的nested XObject资源，全部嵌入、Type3=0；未观察异常缺字或作用域泄漏。字体证据另存`work/layout_candidate_font_embedding.json`。Poppler包没有pdffonts命令，未把未运行的命令写成验证。

**没有声称fontwarning-free。** 完整末次log仍有4类TU/ptm初始shape warnings与Fontconfig配置diagnostic；最终实际PDF字体/缺字检查另行核实。T1已解决实际正文fallback，这些早期diagnostic不被掩盖。

## 6. 剩余范围

本候选只针对基线revision5和现有一张图。根若内联候选、补作者资料或插第二张图，必须以新source SHA重新绑定编译/PDF/页数和布局；当前10页不替代那个验收。四篇全文比较缺口、完整非线性family证书/交付边界均未改变。仍不预测录用或评分。
