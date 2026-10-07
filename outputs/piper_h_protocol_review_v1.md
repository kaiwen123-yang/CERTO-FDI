# PiPER H 预备协议：有限独立审查 v1

2026-10-07。结论：接受为固定官方版本的接口预备核查；上机前需明确两项aggregate边界及二项式共同p限定。未修改原协议/root文件，未执行SDK、CAN、硬件或旧checks，不是whole-source review。

## 版本及实际阅读

协议outputs/piper_h_interface_protocol_v1.md SHA a58fd4011eb48846e9cb20518d7f07af757f07265bc439a6d02e773794b84f31；
实际source audit文件outputs/piper_h_source_audit_v1.json SHA 91a2fb9d3d359e04827522e989e96e2e9b0d0e37eda62e71c9f62ce317a14700。
本地clone remote为https://github.com/agilexrobotics/pyAgxArm.git，HEAD实际为841a625f5f4920e776f20b934eb13048b747e6d0，tracked tree clean。原audit七份source的bytes hash逐一相符，详情见本review JSON。

实际定向读firmware_reference的型号/版本/scale段、API的get_motor_states与model定位、constants静态表、default driver getter/MIT段、parser解码与config scale段、table_driven小类、high-speed报文旧注释。另读arm_options、factory model配置/route、validator.is_joints及四个H thin subclasses。不声称读完180KB API、全部version父drivers、CAN backend、并发/异常路径或整个SDK。旧SDKredirect历史本轮未再次联网查。

只执行git/读取/hash与标准库Fraction/Decimal计算；没有import/install SDK、调用文档示例、connect机器人、发命令或采集硬件。实际H机型/固件/标定未确认。

## 接口主张

1. 型号配置成立。PIPER_H=piper_h，factory按robot选择joint_torque_k/b/c；H与普通piper的关节2、4、5系数不同。四个H Driver都是对应Piper default/v183/v188/v189的thin pass subclass。固件文档所列MIT编码/scale变化有来源，但量程不是硬件额定值或动作许可。
2. Motor缓存成立。driver第584–624行取得parser的motor_state_j对象，存在即返回并填fps的hz，否则None。轮询不是新RX事件。table_driven第39–57行复用cached对象并将CAN Message.timestamp赋给它；这里不能判定该stamp来自设备时钟，亦未证明atomic snapshot。
3. Torque区别成立。parser第91–108行current按signed16乘1e−3，torque=current*torque_scale；第677–694行scale为该joint的config k*b*c。是电流换算估计，不是独立torque sensor。旧high-speed类注释的uint16/单位与decoder/API存在差异，保存raw bytes/config/decoder版本正确；不据代码断言真实标定精度。
4. MIT文档概念reference为kp(p_des−p)+kd(v_des−v)+t_ff。t_ff仅feed-forward，reference也不是实测执行力矩。未来force/health是否沿同一B仍需辨识，不能把缓存直接当主定理full state。

## 必须明示的aggregate边界

R4：get_joint_angles第291–339行固定顺序选择joint_12、joint_34、joint_56。单timestamp来自getter中最后选中的存在缓存（三者都有时joint_56优先），不是这些帧stamp的max或全局最新RX。
静态反例：joint_56旧stamp10、后来joint_12新stamp20；六轴拼合可含新的1/2轴，但aggregate stamp仍10。原“最后更新到的报文变量”建议改为该精确选择规则。本例是源码控制流推论，没有实测或运行模拟。

R5：六轴列表初始全0，只替换存在的帧组；只要任一组存在且generic Validator.is_joints通过即可返回。该validator只核长度/数值/[-2π,2π]，不核三组都received。第一次只有joint_12合法小角度时，其他四轴默认0仍可通过。所以non-None不证明全六轴收到，更不证明fresh/synchronous。
未来collector应逐组保留received/valid、sequence、age/skew；未收到轴标missing，不当数值0；无法映射raw frame身份时freshness=unknown。这进一步明确已有raw-record合同，不是测出的firmware故障或线程安全审核。

## Binomial 2995公式独立核验

针对固定阈值、同一固定分布的独立同分布Bernoulli(p)健康试验，N次零误报的一侧95%上端点为
p_upper(N)=1−(1/20)^{1/N}。
严格p_upper<1/1000等价(999/1000)^N<1/20。
Fraction整数幂核：N2995严格满足、N2994不满足；随N单调，最小整数2995正确。

70位Decimal结果：
- N2995：0.0009997444209011423176791711437842197966207888428560849291556479793290
- N2994：0.0010000781698466700699416135096380117696004030118359086651117345687311

建议原“独立Bernoulli”明确为“共同固定p的独立同分布试验”。不是相关滑窗、调阈值后复用留出、changing contexts或整个健康类worst-case PFA保证。反例：独立N次中一个p_i=.5、其余0，观察全零概率仍.5；不能从该零计数给max p_i<.001。当前文档仅解释证据量，不要求2995次上机或保证实物独立性。

## 预备协议接受范围

Raw RX sequence而非payload去重、三组/六路分别留时间、完整命令/反馈保存但diagnostic mask预声明、健康留出/限定扰动/后处理信号区别、掉帧/饱和/失败保留，均支持准备。绕过mask的其他姿态/关节/commands需重建信息合同。

异步部分输出、current torque estimate不能自动满足known fixed Gaussian common-support/full retained state定理。没有实机Gaussian、stable/rate/commonB或H^{5/2}系数验证，没有动作/硬限幅/forced return保证。PiPER H上机仍是未来另行授权的可选会话；主理论、D2与稿件独立推进。本review仅两份新输出，原source/protocol不变。

## 当前protocol修订的局部binding复核

根在原审查之后修订protocol为SHA ebf843c1195e9b32a4a945e2575b08c2a84cf666a3c2eb06f4fcf77071643832。本轮只复读两处修改段：getter明确12→34→56最后存在cache而非max；partial/default0/nonNone边界与received/valid/missing明确；binomial明确共同固定p IID、非varying-context worstcase。R4/R5/R6的三项澄清已闭合，可接受该current revision为预备接口协议。

原输入a58fd4…、原source-audit 91a2fb…、原2995计算和source读取范围均保留，不将新protocol字节冒称原版本。没有重跑二项式计算、SDK或硬件；当前source-audit JSON仍未改，接口运行/实物验证边界也未扩大。
