# Revision6：有限局部集成与语义一致复核 v1

2026-10-07。**接受当前revision6的局部集成：布局候选到host实际仅一处已授权的closed-subgrid Figure2/text替换，未改主定理、量词或证明。** 当前source/PDF/full-log版本绑定匹配已有新回执。本轮不重新全文证明、科学检查、D2、编译或全页视觉；只写本md/json，不改root文件。

## 1. 版本

|对象|实际SHA256|
|---|---|
|current host R6|8eaa707da6df0c477a946e596ba3bc05522f249e93f806e54288559db55e0e6e|
|layout candidate|d1ba94f30430e9ec9c36b2063296231c518204d17812ac61e8a014691ac16cb4|
|R5历史snapshot|e5d3c2d639e828795518101a78ea08cec56ea8bb1b44a01282186180fc75a371|
|compile/layout receipt v2|1bbbe330528cebaa68af8635daf0509011d69a7c7a6ccd5be0a3cb969652bc0b|
|current PDF|c8e02b022d0c875163499f5a45ff374208376702f1176da66f02bd08665b6195|
|完整TeX log|3c65671bf90deb2e08dafca12f17322cfff902d8b71c860c4f66c43d0ae7e364|

还实际读layout review、root integration脚本、layout before/after记录、R6 receipt、readout caption/有限图review，并读取这些文件、图data/PDF的hash（同名JSON完整记录）。

## 2. 实际diff与布局数学保全

只将work/integrate_submission_revision6.py作为文本/AST读取，不执行其改稿代码。提取其old/new literal：candidate中old仅出现一次，做这一处替换得到的完整文本与current host**精确相同**。因此新增图/文字块以外没有未记录的theorem/proof/quantifier变化。它将“仅H120 pair”扩为已有review接受的H≤200闭合子网格说明，不是新增理论。

本轮对work/submission_layout_edits.json的35条math before/after再独立做有序语义比较：只忽略空白、TeX control-space、quad/薄空白、alignment分隔/换行、display/aligned/split等布局environment、label/notag；不删除运算符、数值或数学字符。35条全部相同。Plateau candidate-set的单backslash-newline是TeX control-space，明确按spacing处理，未当作数学删改。

另把35条布局变更在内存中逐项逆向撤销；剩余actual diff只有T1编码、a_j^h简写定义、s=O(c)澄清和H120表格layout。再撤销这些已授权项后与真实R5 snapshot全文精确相同，六个表math数值cell逐项/顺序相同。故无借排版缩短证明、删除限制或改变常数的情况。没有重跑原exact math scripts。

a_j^h=1_{h=1}a_j只明确原plant含义；s=O(c)精确表达已核文献scaling；T1只处理IEEE text font兼容，不改math packages、geometry或字号。

## 3. Figure2/text的限定语义

实际新增段和caption与d2a_readout_figure_review_v1.md范围一致：
- Prescribed terminal-balanced family，声明H={40,60,80,100,120,160,200}，14条分类/12条数值绘制，非任意calendars。
- H40两条方向退化无risk certificate，未填power0；正文/图注明确数值轴省略它们。
- 所有非退化行保留，包括未达充分power目标；point的零certificate下界不叫actualpower0。
- Average第一个certified grid point H100，总26秒含4槽prefix；不是连续最短、全日历最优或sequential stopping。
- 不同H各自有预声明calendar，该H两个readouts共享它；不是单条online路径逐步截断。
- Variance对象是full-history Gaussian comparator上的prescribed statistic；direction有有理Euclidean norm缩放，而statistic未除标准差。Weights随H/readout变，variance ratio不叫universal readout improvement。
- 真实nonlinear统计量另用remainder/events保护；图不instantiate linear asymptotic theorem，固定ramp/继承条件仍在surrounding text。
- Full400未完全certified，closed subgrid不冒充其完成；连接线不是数据频率/CI或网格间认证。

图PDF、caption/data/review的当前hash已核，与既有有限review绑定相同。本轮没有重新读取38个case叶文件、算PFA/variance、生成图或跑D2；继承的是图review的有限证据，不扩大它。

## 4. Label、bib与版本连接

Current host有49个唯一label，无dangling ref/eqref；相对candidate仅新增sf:readout-figure，无删除。13 bibkeys和顺序不变，cite无missing key。既有四个fulltext comparison gaps保留，不从新Figure2或font修复推断历史优先性。

Host字节TAB=0、孤立CR=0、其他低控制字节=0。实际source/PDF/full-log的hash分别与compile_layout_status_v2.json字段相符，R6 receipt也绑定candidate/当前source。这里不是只看静态便称编译成功，而是核已有实际compiler回执所指的真实字节。

## 5. 编译/视觉证据的承担者与限制

已有root回执记录Tectonic CLI exit0、11页、full-log Overfull0、missing/undefined0、28字体流嵌入、无Type3，并记录root实际读全部11页。我们只继承这一版本绑定结果，没有再次调用compiler、render PDF或独立视觉读全页。Underfull/初始font/Fontconfig warning仍保留，不能称warning-free；native editor旧platform failure与既有CLI成功分别记录。

该接受范围不含真实作者metadata/bios/photos的最终页数、full400、四项外部全文比较或最终actual ZIP验收；不是TAC submission-ready结论。原R5超宽/旧审查和原7ced数学body绑定继续作为历史，不能改称当时已编译/layout通过。

