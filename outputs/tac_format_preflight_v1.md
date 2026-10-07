# TAC 格式预检 v1

2026-10-07。本次复核仅依据当前 IEEE CSS／TAC [Author Information](https://www.ieeecss.org/publication/transactions-automatic-control/author-info)（AI）和[期刊官方页](https://ieeecss.org/publication/transactions-automatic-control)（TAC）；重读既有 `tac_venue_check_20261007.md` 与引文预检。**这是 PDF 验收清单，不宣布整稿已通过投稿验收。**

| 检查项 | 当前官方规则／验收处理 | 来源位置 |
|---|---|---|
| Full Paper 篇幅 | IEEE journal双栏、single-spaced；通常12页，硬上限16页；超过12页有overlength charge | AI §1；TAC General Information |
| 作者照片／简介 | FP须置于文末，并计入页限；TN不得包含 | TAC General Information |
| 附录／参考文献计页 | 官方给整篇页限，没有在所读两页列出二者豁免；**当前按整份主PDF计页**。此处理是全稿页限的保守执行，不伪称官方另有逐项明确句子 | AI §1；TAC General Information |
| 摘要／标题 | FP摘要单段≤300词（TN≤75）；无公式、引文、脚注；标题无symbols | AI §C.1 |
| 作者／匿名 | 首面要求作者姓名、单位；各作者地址、电话、email、fax及通信地址。未见匿名指令；不假设double-blind | AI §C.1 |
| 正文／书目 | 引言明确purpose/contribution；合适时结论写优点、限制、应用；文末完整IEEE编号书目 | AI §C.2–3 |
| Supplement | 可另传supporting files及cover message；所读规则未说明文件大小／格式、评审或归档保证，也未授权将承重proof移出主稿来认定合规 | AI §A |
| 模板／纸张 | 使用标准Transactions模板；不得超出normal parameters改模板；PDF可按US Letter打印并须实际检查 | AI模板注、§A |

若改选Technical Note，则通常6页、最多8页，并使用上表TN摘要／bios规则；这不是本稿当前类型建议。[官方条目](https://ieeecss.org/publication/transactions-automatic-control)

作者占位是单独的行政待填项。现读源码首部为`\author{Author information to be supplied}`（第9行）；作者身份、单位、联系方式、通信作者、真实photos/bios、资助及既往会议／投稿关系需用户提供，不能代造。其完成情况不能由技术证明或引文检查代替。

门户转换要求另见JSON：只有选择其LaTeX自动转换时才要求ZIP内主文件叫`root.tex`；无需据此重命名当前编辑文件。官方对自行上传的**pdfLaTeX** PDF另写`\pdfminorversion=4`；没有说明Tectonic输出，不能扩写成所有引擎的统一版本要求。[AI §A](https://www.ieeecss.org/publication/transactions-automatic-control/author-info)

根的当前PDF验收应核：整份主PDF≤16页并为真实作者bios/photos预留容量；摘要及首面；正常IEEE双栏/Letter；完整proof与13条书目能阅读且无裁切。实际页数、图片/公式视觉检查与编译结论由根记录，本报告不重复认证。

**就格式规则而言，下一步是完成根的PDF检查并补真实作者资料；首要剩余格式风险是不能把“无bios的技术PDF页数”当作最终FP页数。** 四篇全文比较缺口仍属引文／历史覆盖问题，与作者资料待填分开，本轮未重新检索。
