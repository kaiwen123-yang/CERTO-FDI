# D2-a 三完整块主例：H160 pair 有限独审 v1

2026-10-07。**接受H160 terminal-balanced average作为预声明网格中最早同时满足“至少3完整块”和认证目标的主例；其point配对仍是有效证书但未达充分power目标。** 这是旧冻结实验的小元数据选择/绑定复核，不是新science运行或全表接受。

## 冻结范围与先验选择

使用已独审figure data SHA8022e863c9b74179f01c3452e0028ab489aa84b7111823b8bd811aab2a816e97的14行；protocol仍0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6。没有新增H/日历/阈值或为通过调物理参数。

H是post-prefix slots。H160有3完整symmetric blocks、6moves，总41000faststeps、41秒（含4槽prefix）。Actual ramp最大3/250=0.012，属于已审H≤600/f≤.045域；不覆盖历史wide.75。两个readouts共享该H同一physical calendar。

|更早/当前H|blocks|average分类|≥3且certified|
|---|---:|---|---|
|40|1|direction退化、无risk certificate|否|
|60|1|valid certificate目标未达|否|
|80|2|valid certificate目标未达|否|
|100|2|certified pass|否：少于3块|
|120|2|certified pass|否：少于3块|
|160|3|certified pass|是|

H100仍是该family的first certified grid point（26秒）；它与“按原≥3选择主例”是两个问题，不能改写旧H100/H120历史或图。H160结论只对声明网格及该family，不是continuous/sequential或全family最短时间。

## Pair endpoint（下面仅显示近似，精确值见JSON）

|量|average250|point_last_fast_read|
|---|---:|---:|
|Vminus|≈6.15681250576e−7|≈0.0181101064075|
|Vplus|≈6.19105139359e−7|≈0.0181313301024|
|Vplus/Vnom upper|≈1.00279758015|≈1.00058713302|
|mu0 upper|≈0.0146587239274|≈0.0229380381124|
|mu1 lower|≈0.0484979035265|≈0.0405504843627|
|b0、b1（每侧）|≈0.00114819240771|≈0.0232685923921|
|dynamic mean loss（每侧）|≈0.000857480863568|≈0.00909848767773|
|event budget（每假设）|≈2.73873470953e−11|≈2.73873470953e−11|
|PFA upper|≈0.000967122598651|≈0.000967122598651|
|protected gap|≈0.0290839437051|≈−0.449714199584|
|protected power lower|≈0.999999999973|0|
|分类|CERTIFIED_TARGET_PASS|VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET|

显示值为round-to-display，不能作为risk计算端点；尤其Vplus/PFA upper和power lower若要直接当上下界表值，应按精确Fraction朝保守方向取整。JSON保留原精确有理字符串，包括threshold、standardized gap及所有要求字段。

两个精确PFA均<1/1000；average精确power≥9/10、variance ratio≤101/100。Point gap<0且power bound=0，不是actualpower0；没有把Vplus同方向代入负gap给正power。两侧完整健康path和每侧error/event仍各自支付，equal uniform bounds不要求共用nuisance。

## 版本绑定与实际复核

同名JSON包含两case的CASE SHA、selected current receipt path/SHA、frozen direction record path/SHA、projection certificate SHA、covariance/witness的已绑定SHA。实际读取/哈希仅小文件CASE/current receipt/direction/projection；projection内容等于frozen record中的projection。大ADJOINT witness没有读取或重新hash，covariance/witness hash来自既有接受绑定，不把它描述为本轮大科学验收。

CASE与receipt的case hash一致；3blocks/6moves与calendar/冻结row一致；protocol和mean-review hash均相符。Mean review仍6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924。通过静态AST取source函数文本（不import science）核mean_certificate SHAa6e618bddb0157dc8c48d59c219114f22cc73b4b16bc0d11f1f9814991306391与review绑定一致；guarded_risk、target_classification、terminal、normalize_raw及当前文件hash另在JSON列出。

本轮核gap=m1−b1−threshold、先前网格成员完整存在及eligible谓词，未重新算均值support、尾界、large recurrence/KKT optimizer或全R1证明。原H120历史和whole14-row图保留。可以作为root把主例改为H160的有限证据门，但当前主稿未由本代理改动；未来host/PDF仍需新hash/布局绑定。

