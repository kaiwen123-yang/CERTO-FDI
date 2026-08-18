# Review Package Contract

## Thin package

适合上传给 GPT/Claude，目标 < 50 MB：

- `00_READ_ME_FIRST.md`
- `01_INDEPENDENT_REVIEW_PROMPT.md`
- search log / PRISMA flow / evidence counts；
- top 25 direct-neighbor method cards；
- literature/novelty decision memos；
- dataset registry, schema, split and license matrix；
- native/universal baseline summaries；
- candidate comparison and decision evidence；
- code snapshot、configs、tests、Git provenance；
- selected figures；
- SHA256 manifest and smoke script。

## Full package

包含全部文本结果、CSV、JSON、logs 和小型复现样例。

禁止：

- 再分发许可不允许的出版商 PDF；
- 打包公共数据原文件；
- 打包密钥、cookie、institution login；
- 把付费全文复制进审查 ZIP。

对文献全文只打包：

- bibliographic/access manifest；
- 本地文件 SHA；
- 阅读卡与页码引用；
- 明确允许再分发的开放全文（若许可允许）。

两包必须通过 CRC、全新解压、内部 SHA、拓扑、secret scan 和 smoke。
