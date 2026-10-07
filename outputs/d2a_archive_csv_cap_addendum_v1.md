# D2-a exact CSV metadata cap 限定补充 v1

2026-10-07。**CSV cap一致性修复与真实小 ZIP fixture通过；未执行全科学归档/replay、R1或真实大witness hash，`scientific_ready=false`。** 本补充不改前30项IO和22项coverage的任何source/report/receipt历史字节。

原recipe `small()`实际统一4,000,000 bytes，而immutable selector统一2MiB。helper和coverage对精确 `work/d2a_cert_review_bound_table.csv`已允许16MiB。完整400表可能超过2MiB，旧selector会静默略去该必需表，snapshot也可能拒绝其更大版本。

当前recipe精确表路径统一允许 **16MiB = 16,777,216 bytes**；其余小文件统一 **2MiB = 2,097,152 bytes**，没有其他CSV path例外。`small()`在stat前门和实际read后均检查cap。immutable selector对required TABLE超过16MiB明确抛错，且在创建metadata root前拒绝；其他>2MiB项不进入small view，原payload仍属于archive全文件hash/replay范围。selected original small view总量明确限制 **256MiB = 268,435,456 bytes**，不扩大helper/coverage原总cap。

实际执行 `python -S -B -X utf8 outputs/d2a_archive_csv_cap_fixtures_v1.py`：**26 checks、0 failures**。真实ZIP208,103字节含2,877,304字节synthetic CSV；从actualZIP完整提取和hash，Windows readonly，snapshot `small()`逐字节读取，coverage绑定全部synthetic400 rows/3 science rows/2 cases。该synthetic数据不代表真实科学证书。

边界fixture证明：exact TABLE16MiB通过、16MiB+1拒绝；other2MiB通过、2MiB+1拒绝；required TABLE超限不会被静默filter或留下partial root；otherCSV超2MiB仍排除；256MiB总量拒绝门未放宽。全量snapshot、active CSV写入、science/R1或大payload读取均未执行。

当前 `package_full_d2a_release_v2.py` SHA256 `1adc2b0e1acb326e9e63c8a852fa35d3b648abe553484b63f8cdbede8b842953`；新fixture源SHA `4c5957026dc6d6ded729e4e98e8be51f0d5494f6b188c6173fc29a8a7ebdfa53`。

上一coverage版recipe实际字节在 `references/release_recipe_history/97e36639d9291e72a93c84c822749f79eaa55d15af13c7bc5ff683916b5ee50f.py`，SHA与文件名完整相同。首版IO recipe `1c6ecc8e...`同样保留历史实字节。前IO/coverage源、fixture/results/addendum及V1合同均保持其历史绑定；本补充JSON列完整hash。最终独审须读三层历史和当前recipe，不把26项cap fixture扩写成full科学验收。
