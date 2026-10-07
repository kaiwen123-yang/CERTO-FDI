# 理论代表图：记忆收益与齐次恢复时长

主张：相同标量物理输入/噪声下，固定缺测长度的记忆收益，在支付同一个齐次恢复时长后变成分段优化问题。

数据为解析有限和生成的有理c网格（不是测量样本）；k由精确Fraction幂确定，gamma=.81，D_move=0，c∈[.8,.95]。不删除端点，不把ceil等号算到下一plateau，不跨jump连线。

- (a) 缺测罚kappa：fixed k=1对照与qualified k(c)曲线。角色为主张锚点；填实的右端点属于较短k，空心上跳点为不可达到的右极限。
- (b) 资格所需的最小整数k(c)。角色为可行性定义桥梁；与(a)共享c范围，用整数ticks，端点约定一致。

推荐piecewise解析线加exact endpoint markers；没有随机数据，不画置信带/均值柱/显著性。备选为compact候选点表，已有精确表保留caption里的关键值；额外near-unit发散曲线放补充，避免一图塞入第二种极限。

图注必须说明：这里只是homogeneous qualification，不是全含噪/受迫return或hardware tracking；三点族c=.9最佳，完整区间c=.81最佳由精确候选证书决定。图中小数仅显示，不作为排名依据。

最终计划尺寸7.16×3.1in，8pt标签/刻度，PDF/SVG矢量优先、600dpi PNG与灰度预览；机器layout和人工读图均验收后再导出矢量。结果段落对应“Settling time changes the controller comparison”。
