# 决策与分支记录

## 2026-10-07：初始化长期目标任务书

用户要求：给出长期计划，随后准备开启/goal，尽可能自主推进至确实需要外部条件或用户决定。此次仅做启动准备，不提前创建goal。

选择：保持一篇TAC理论稿。主线为闭环记忆、健康漂移与切换缺测共同决定的信息极限；备选为固定有限健康盒的有限时域过渡；D2-a为并行支撑线。PiPER H暂限接口和实验协议；完整6R D1.b按理论需要决定优先级。

理由：已有iid论证不能自动推广到有色全史模型；已有固定日历验证不能关闭D2-a；机器人实现和通用稳定性工具本身不能替代主理论增量。

证据：`../references/audit_20261007/research_review.md`、`../references/audit_20261007/TAC_THEORY_ROADMAP.md`、`../references/audit_20261007/r1_verification_receipt.json`。材料来源和哈希见`../source_index.json`。

后续变更规则：每次修改模型、信息结构、策略类、风险指标或切换主线，记录触发证据、旧版本、受影响主张及必须重审的结果。反例和失败版本保留，不用新标题覆盖旧结论。

独立计划审查修正：首项sharp要求同一范围内首项常数匹配且各自余项相对首项一致可忽略，不要求上下界余项表达式完全相同；避免将不必要的高阶匹配设为完成门槛。审查仅针对执行计划，不是主理论证明审查。

## 2026-10-07：用户启动goal后的第一轮研究

已读用户附件中的原长期计划，目标保持完整。上一轮是启动准备，当前goal turn实际推进证明、源码、文献和新证书；进展分类为progress，无全目标阻塞。

合同M0采用原始观测Y=s b+a+epsilon，变换任务符号必须同步变换协方差。原iid主稿在本地ADMISSION_REVISION完整ZIP中找到，按原样导入并与归档成员绑定。原稿只定向审查sharp/finite两条主结论，不能升级全稿验收。

第一版AR(1)主逆界固定n0≥1，利用前缀与末尾支配把缺测化为内部gap；n0=0、强制终点任务、额外传感、数据自适应策略均未借用本逆界。这是当前结果的明确条件，长期主稿范围仍依后续证明决定，不能据该阶段结果缩小goal成功标准。

D2-a边界选择：点读数为同槽最后现有pre-step快样本n=250(s+1)-1，采样时刻与槽末可用时刻分列，不新增终点创新。该约定在新风险计算前冻结；设计模板与实际sampled fault mean分别处理，原物理参数不改。

本轮发现错误all-z constant-gap替换桥梁：合法恒值健康路径在任务跳变处产生H^(5/2)误差；该路径不一定最小化，不能借此否定profile后候选。保留exact raw边界可给全类O(H)接口，主逆界用zero-endpoint对手避免该错误。

审查接受有色liminf下界，不据此称sharp。匹配上界、真实控制系统桥梁、完整D2-a表、稿件与实际交付验收仍需继续。源码编译平台故障不阻塞其他研究；保留TeX及unverified状态。

## 2026-10-07：匹配证明、物理矩阵主线与稿件收敛

后续完成M0匹配上界且根独立审查接受；M1和正定噪声M2通过内部独立逐式审查。现在把同一物理输入/噪声下的矩阵闭环结果作为论文中心，M0留为独立模型对照，不把其均值结构和物理force-filter结构混为同一合同。

M2S为单独声明的奇异噪声扩展，不覆盖或修改M2。B必须落在noise range；Gaussian共支持通过SVD和真实predictor的rowspace证明，禁止伪逆congruence捷径。beta=0时可能恢复常值fault score而非全部inputs，正定噪声严格正beta的条件具有控制结构意义。更强Theta(H²)尚待独立审查。

保留M1/M2冻结v1与review哈希；编辑修正和asymmetric nonzero repair计算写成v1.1/独立补充。原对称检查repair全0的coverage局限公开记录，不把数百条零修补记录称为一般修补覆盖。

D2-a数学审查接受固定ramp的实际f≤.045范围，未接受旧wide .75 mirror。唯一活batch PID59248/owner-scoped session94963继续运行；review-bound表为当前权威。原wrapper失败保留，并以派生-S回执修复，不能靠删行或改参数通过。全表尚未结束，部分H*仅在对应族所有早期和当前成员闭合后报告。

目标仍完整：不把任何新定理、有限证书或阶段报告称为TAC投稿稿已准备完成。下一步着重一个主稿的证据整合与独立反方审查；硬件仍是可选，6R高阶只按实际理论收益推进。

## 2026-10-07：完成整稿内审、字节复现与持久计算恢复

M2S两个分支和共同-SPD紧致控制器族桥梁均独立接受，单一英文技术稿已内联完整证明。整稿1265行完整阅读发现正/零分支主张同步、块起点/中心和nonlinear风险接口缺口；revision4修补并定向独审闭合，没有借修辞扩大数学合同。四个全文比较缺口、真实compiler/PDF/IEEE页数和全400风险结果仍待验收。

实际理论阶段ZIP98文件新解压，97个payload hashes和11个独立标准库程序全部通过并匹配保存JSON；不将它改称完整TAC/D2-a release。D2 runtime snapshot450文件封存，记录实际bootstrap、原R1 SHA和还必需的大witness/history。Git属性保留精确科学字节，不改全局配置、不格式化来源快照。

长计算旧进程OS确证消失、日志停在生成而无完成；只有截断S140 average witness需重生成，原65MB字节按hash保留。初次detached恢复发现真实Windows共享锁atomic替换失败，有限重试与实际回归修复。新科学62844/metadata10032经WMI独立隐藏launcher启动，根在拥有代理结束后确认仍存活；不再把agent-scoped旧94963当可用句柄，不凭过时alive JSON重启。

2012两篇直接feedback/AFD原文在23个新公开入口及现核本地Zotero只读查询仍未取得。metadata页码冲突以CrossRef/作者交叉证据纠正，但不把未读全文升级为模型/定理比较。此限制不停止其它已授权研究工作。

## 2026-10-07：统一IEEE稿、实际PDF与有限证书图

统一common-support框架替代重复model/proof；完整承重证明保留，35个display仅布局变化且token/数字顺序一致。默认native平台故障经既有Tectonic CLI绕过，修missing-item与双栏越界后currentR6 actual11页全部读取、字体嵌入/几何合格。两图分别为解析settling与closed H<=200有限证书，不将其混为实机/全400验证。PiPER_H官方静态接口协议补cache/异步/torque/time合同，硬件仍可选。四缺全文及full400/finalZIP仍开放，原目标没有缩小。


## 2026-10-07T10:19:46.495054+00:00：R8风险意义与最终科学归档准备

保持原goal、主模型和冻结物理协议。新增推论只转译已审信息亏损为固定终点风险代价，完整处理整数舍入、全部更早终点、真实calendar/test存在及commonSPD near-inf；copy-plant例排除零分支普遍正代价。最终fragment及R8两insert各自独审绑定。

原代表例≥3完整块条件由H160/41s满足，H100/26s仍为族首有证网格，保留H120和旧稿。C1/C2 source修复不改科学；sole publisher自然加载，避免第二写者。最终release另建原metadata只读view与真实ZIP presence IO，补齐科学canonical覆盖门；小fixture/source审查不能替代尚未执行的大科学重放。V2含R6历史，currentR8和future finalrelease分开。


## 2026-10-07T10:53:14.407134+00:00：预演完成、用户审查暂停

actual pair science各1次，原数据47前后hash/48ZIP/freshR1463闭合；两次环境失败均保留、无science重复。P6精确有限预算判定仅支持当前point接口无需为收紧余项开启6R。用户明确选择“当前预演后暂停goal，后台计算继续”，并确认替换kaiwen123-yang/CERTO-FDI供审查。原长期目标未完成或缩小；不停止两后台job，后续GitHub发布是本次另行授权工作。
