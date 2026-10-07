# D2-a turn 2：只读进度、族闭合与 regime 诊断

2026-10-07，现场窗口07:24–07:26 UTC（本地15:24–15:26）。没有启动/重启science、改源码/锁/runtime/表、读取大gzip payload或重跑科学递推/验收。仅拥有本新文件。

## 真实OS进程与资源

CIM两次确认唯一serial science62844、metadata10032存活，两者parent71048已退出；没有unified exec session。旧59248/63968、旧94963/1590和原child70120不在OS列表，不据此猜测旧退出码。

- 07:24：真实child29504，parent62844，python -S verifier核H240 terminal_balanced average250。
- 07:25:34：同child已用CPU114.39秒，working set774,852,608字节；创建于07:23:39。producer小checkpoint COMPLETE不能先称独立验收完成。
- 07:26:15：average250已出现PASS_STDLIB_NEW_CASE_VERIFIER receipt；新child30308开始H240 terminal_balanced point_last_fast_read的GENERATE_DEGREE8_ADJOINT_WITNESS。Supervisor/metadata仍活，是真实推进。
- Detached science/publisher stderr尾部本轮为空。
- C盘free161,210,933,248字节≈150.14GiB，高于worker25GiB保留线；下一case缓冲仍由原worker守门，不保证全部余下case所需总磁盘。

没有停止证据，不重启。若后续确证supervisor停止，先向root报CIM缺席、日志/锁/最终phase和可得退出码，再由原恢复流程决定续接；publisher快照数分钟不变不是停止证据。

## 权威表、范围与历史

实际读取的work/d2a_cert_review_bound_table.csv为1,332,501字节，SHA256
b5ffe06df9ce1ee12fe1094c7ff5415763ee402522eff8d1dc4e4b21fd65e7c6。
其receipt、publisher round14（07:21:29 UTC）、partial-H JSON输入SHA均相符。

|发布分类|行数|
|---|---:|
|ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE|74|
|VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET|65|
|CERTIFIED_TARGET_PASS|31|
|NOT_RUN|230|
|总计|400|

170行已有分类，仅96行是完成mean/variance/risk认证的非零方向行；74行是声明方向零/舍入退化，不应叫74次完整科学计算。304行arithmetic_risk_target_status为空，含74退化及230未算，不能混为失败。96非零完成行的CASE/current receipt/witness/covariance/mean review绑定字段均非空；本轮只核轻量字段及表SHA，未重新读全部大witness核实际字节。

协议实际文件SHA重新核验为0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6；mean review实际SHA为6a9cfb8009d2b424dfd29130c3d9140478531aeb74b326e917881eb35d7fe924。接受范围固定ramp f(t)=3/10000 max(t−1,0)、H≤600、总时域≤151秒、actual f≤9/200=0.045及继承条件。原0.75物理fault allowance不变，但wide-fault mirror containment未接受；不能把本表当整个0.75盒认证。

两条旧wrapper失败仍在batch execution_failures及表历史列，resolved=True：
- H80 fixed40 point：stdlib_verify_EXIT_1；当前receipt SHA8d8949f43e463414f53c020b517e2c022e364f305803662f350a8c7e1faefe4a。
- H80 switch_then_stay S60 average：同原失败；当前receipt SHAf830d4477770e570f21c06f2f93a52d30fc6d919b7c9e44e46def549208c679a。

H200/S140 average的原截断gzip INTERRUPTED归档现场存在，长度仍65,755,445字节；本轮不重读/哈希大payload。原SHA5711395f5a81e7f2e6b53f80f2eba89bcc62c4ab8ec7802a4f2d02760c6145f8、缺EOF和只该case重生的历史保持。另一次WinError5是cache-view atomic replace冲突，不能叫数学证书失败；bounded retry已有原独立PASS，本轮不重跑fixture。

## 已闭合族与部分首次成功

所有H≤200的全family/S/readout rows现场按risk_status核无NOT_RUN。
H240共34行：6退化、3pass、3目标未达、22未算；H300共40行：6退化、34未算；H400共50行：6退化、44未算；H500的60行和H600的70行均未算。

partial-H绑定同一表SHA。五个average250首次成功pairs的更早网格及选中H全族成员均现场核闭合：

|family|部分first-success H|前一网格H|总终点秒|
|---|---:|---:|---:|
|fixed20|100|80|26|
|fixed40|120|100|31|
|fixed76|100|80|26|
|terminal_balanced|100|80|26|
|switch_then_stay|100|80|26|

switch_then_stay选中S=100。predecessor_grid_rows_complete和family_selection_at_H_complete均True，但all_grid_complete均False；只表示预声明有限网格/认证程序的部分首次成功，不是连续最优时刻。Stay和全部point pairs目前first_success=null，不能解释为全网格无成功。

07:26:15已新增H240 terminal_balanced average独立PASS receipt，CASE SHA8a5de29f45e0eb84de4acb27758b5d795bc4fc73c702287fac7b6b99577db8b1；summary为power_lower≈0.9999999999593、false_alarm_upper≈0.000967122612。此时publisher仍round14，因此本文件不擅自把新行加入权威计数、不手动刷新发布表；由metadata正常纳入。

## 已完成行的 readout regime 与图设计

发布计数分readout：average250为37退化、17目标未达、31pass、115未算；point为37退化、48目标未达、0pass、115未算。仅在声明readout、fixed direction与充分认证规则内成立，不证明任意detector最优或实机结论。

H200四个普通族全部闭合。average的Vplus≈5.30–5.95×10⁻⁷；point≈1.81313×10⁻²。以terminal_balanced为例：

|读出|mu1_lower−mu0_upper|adjusted gap|standardized gap|protected power下界|
|---|---:|---:|---:|---:|
|average250|0.05583584|0.05074252|65.81|≈1−3.41×10⁻¹¹|
|point_last_fast_read|0.03689454|−0.43822395|−3.256|0（保守证书）|

Point的0不是actualpower0。两者false-alarm上界≈0.0009671、event预算≈3.4×10⁻¹¹；当前目标未达体现在误差/噪声余量，不能写成事件预算耗尽。Vratio接近1说明新方向方差界紧，不证明iid或锐律系数已迁移。H200 switch_then_stay的S=100,120,140,160,180,200在average均pass；其他成员仍应逐行显示。

展示建议（不生成图、不新算science）：
1. 分readout的H×family/S状态图，四分类分别编码；NOT_RUN留灰空、direction-degenerate另纹理，不能都画失败。
2. 对闭合H≤200画平移不变的margin budget：Δμ、b0+b1、(25/8)√Vplus及adjusted gap。dynamic_loss已进入均值界，不能重复扣；标明实际采样算子。
3. 部分first-success图标清已闭合前驱、有限网格与右侧未闭合；average功效接近1已饱和，margin图更有解释力。

完整400表、全族H*和实际新发布包验收尚未完成。后续继续分别报告真实OS、当前case和authoritative metadata。

## 同轮发布更新：07:26:45 UTC

本文件写入期间metadata正常推进到round15，没有手动刷新。新权威表SHA10e692d2198cf301af84362089b19b0ac61fb32ceb4f4d980df31a73ca3e4513，现场重新读取表字节并核receipt相符，partial-H输入SHA也已同步。400行计数变为74退化、65目标未达、33pass、228未算。H240为6退化、5pass、3目标未达、20未算。

H240新增两个pass行是terminal_balanced average250及switch_then_stay S240 average250；后者是已预声明的同实验identity/cache复用成员，不能把两个逻辑行称为两个独立新科学递推。五个已确证部分first-success H不变；当前H240全族仍未闭合。以上round14诊断保留为实际读取快照，新总数以此round15为准。
