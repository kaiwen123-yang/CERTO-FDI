# D2-a 部分首成功网格证据 v1

2026-10-07。协议SHA256：`0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6`。均值/风险数学审查仅接受固定模板、H≤600、实际f≤0.045及明确继承条件。全400行扫描尚未完成。

| 读出 | 日历族 | 已闭合首成功 H（起点后槽） | 含4槽前缀总时间 | 当前H成员选择 |
|---|---|---:|---:|---|
| average250 | fixed20 | 100 | 26 s | 单一成员 |
| average250 | fixed40 | 120 | 31 s | 单一成员 |
| average250 | fixed76 | 100 | 26 s | 单一成员 |
| average250 | terminal_balanced | 100 | 26 s | 单一成员 |
| average250 | switch_then_stay | 100 | 26 s | 全部S成员已处理，按冻结规则选S=100 |

每一条首成功均先检查该族**全部更早声明网格成员**有有效风险结果或已分类的方向退化；当前H的全部族成员亦已处理。switch_then_stay的重复成员仍有独立表行及证书引用。JSON保留精确风险分数、立即前一个网格值和所选证书目录。

JSON还绑定读取时的review-bound总表SHA及所选行的direction、CASE、当前标准库回执、covariance证书、witness和mean review SHA。冻结preflight方向记录逐行校验；当前H成员尚未闭合时不会提前填入可发布的首成功H。

stay与全部point族仍未闭合首成功。`null`代表当前没有可发布的H*，**不代表全网格失败**，也不代表物理不可检测。后续完整扫描可能补出它们的成功或明确无成功结论。

H*只属于预声明网格、有限日历族、固定方向及认证流程；不是连续最短时域、全体检测器minimax最短时域或随机序贯首报时间。无效/未通过证书不等于真实功效低。

可复查文件为 `d2a_partial_first_success_v1.json` 与同名`.py`。在本仓库运行：

`python -B -X utf8 outputs/d2a_partial_first_success_v1.py`

它从当前review-bound总表重建结果，只对前驱和当前成员闭合的族发布首成功，保留所有未完成族状态。脚本使用`work/`中的已冻结辅助模块，不重新生成jets或执行大递推；最终可复现包尚未验收。
