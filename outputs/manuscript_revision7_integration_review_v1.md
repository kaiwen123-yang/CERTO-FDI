# Revision7：三块代表例局部集成复核 v1

2026-10-07。**接受这次有限示例替换：真实R7全文恰等于R6的八处计划literal替换；主定理、全部proof环境、Figure2源码和参数合同保持相同。** 本轮只写本md/json，不执行root改稿脚本、不改main/ledger，不重读旧proof、不跑D2/旧checks/编译/PDF。实际编译和页面验收由root另绑定。

## 1. 版本与实际差异

|对象|SHA256|
|---|---|
|R6真实历史snapshot|`8eaa707da6df0c477a946e596ba3bc05522f249e93f806e54288559db55e0e6e`|
|R7 actual source|`a26c945e35a8da9c598a5b94fe34f528a19025a652b335a457c4f9fa65626eca`|
|静态读取的root脚本|`cc9329b0d515732e8de465e87b19d36010ce642d7bee09ba3356f7dc973630a5`|
|冻结14行figure data|`8022e863c9b74179f01c3452e0028ab489aa84b7111823b8bd811aab2a816e97`|
|已有three-block选例review|`ff64a112a69879ae12449d7ee79e1c66f4dedc7251c803180b3dc4c9fb63a8e8`|
|R7 receipt|`899352630d72eabe9210a2d699301fb1248ae1ba7bc8c6150b3be99bbcc6ae37`|

脚本用AST/literal读取，没有执行。八个old在R6各出现一次；内存依次替换得到的全文与R7逐字相同，逆撤全部八处又恢复R6全文。其余任何文字都未改变。49 labels和13 bibkeys顺序不变、无dangling ref；全部theorem/proposition/corollary与proof环境文本直接相等，Figure2包括caption也相等。这个证据只验局部diff，不冒称重新证明全稿。

## 2. 选例与风险来源

8022冻结数据的H160两读出均为3个完整对称块、6次transfer、总41秒，已有mean-risk scope为ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN。更早average网格H40/60/80/100/120均小于3块，因此H160是“至少3块且average风险目标达标”这一预声明主例准则的最早声明网格点。该准则仅选illustration，不增加每张证书的合格前提。

average精确Fraction满足PFA<1/1000、power lower≥9/10；point的PFA同样达标，但gap<0、保守power lower=0。新段明确point仍不满足充分power要求，并保留actual power不是0的区别。H100/26秒仍是terminal-balanced average的first certified grid point；H120/31秒记录在冻结Figure2/source data与真实R6历史内，不被删除或改称失败。

root脚本需已有独审选例文件并核两侧direction/current-receipt/evidence-binding小文件hash；本轮核receipt与该review/data的hash连接，不重跑那些科学verifier。新数字只继承冻结case，不改变fault、noise、readout、calendar、physical或mean/event合同。

## 3. 精确数与显示舍入

每个显示值转为Decimal再转Fraction，与冻结exact rational比较；非零显示误差均不超过该末位单位的一半，零point power精确相等。两侧b/event/PFA的相等性也从exact string/Fraction核对。表内向上/向下是显示舍入方向，**不是声称显示小数本身为可重新运算的保守endpoint**。

|量|显示值|相对exact|核查|
|---|---|---|---|
|`avg_b0`|`0.001148192`|向下|通过；只作显示|
|`avg_dynamic`|`0.000857481`|向上|通过；只作显示|
|`point_b0`|`0.023268592`|向下|通过；只作显示|
|`point_dynamic`|`0.009098488`|向上|通过；只作显示|
|`event_each_side`|`2.73873e-11`|向下|通过；只作显示|
|`avg_Vplus`|`6.1910514e-7`|向上|通过；只作显示|
|`avg_gap`|`0.0290839`|向下|通过；只作显示|
|`avg_lower_power`|`0.999999999973`|向上|通过；只作显示|
|`point_Vplus`|`0.0181313`|向下|通过；只作显示|
|`point_gap`|`-0.449714`|向上|通过；只作显示|
|`point_lower_power`|`0`|精确|通过；只作显示|
|`PFA_each_side`|`0.000967122599`|向上|通过；只作显示|

特别是average power exact为约0.99999999997261265，显示0.999999999973向上；point Vplus exact约0.0181313301023552，显示0.0181313向下；event exact约2.7387347095324e−11，显示2.73873e−11向下。原稿的“display decimals不用于risk，使用exact rational/interval endpoints”句完整保留，因此这些不被升级成literal计算保证。mean endpoints已经付dynamic loss；新段仍另付physical-comparator discrepancy，未重计同一损失。

## 4. 未改变的承重边界

R7仍固定H≤600、ramp实际f≤0.045及继承返回/事件条件；没有扩大旧force box。完整400未完成、当前closed terminal子网格而非任意calendar optimum的限制保留。≥3选例不是sequential stopping、continuous最短或all-calendar最优；四篇全文比较缺口和信息访问合同不变。此报告不认证新PDF/page count，也不升级为全稿数学再接受或投稿就绪。
