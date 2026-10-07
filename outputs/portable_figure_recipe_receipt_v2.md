# Figure 1 可移植重绘入口

冻结的 control_settling_figure_v1.py 和原图/QA/数据均未改。新增 control_settling_figure_portable_v2.py 只替换本机skill依赖的预览/画布边界QA，并要求单独输出目录；解析有限和、端点、数据和绘图代码保持原顺序。

使用同一Python3.12环境，先在 work/portable_figure1_v2_data 执行data-only，1202行CSV与冻结原文件逐字节相同；随后在另一个目录渲染预览，根实际查看，两种曲线、端点约定、最优点及文字均正常，之后导出PDF/SVG/600dpiPNG。没有用重绘结果覆盖主稿引用的原图或改变其SHA。

可移植入口仅需要matplotlib/Pillow及相邻冻结CSV，没有绝对skill路径。命令：python outputs/control_settling_figure_portable_v2.py --output-directory work/figure1_preview；查看预览后可加--export。需要重新生成数据时加--data-only，其输出仍在独立目录；原文件保留。

机器QA只检查可见文字是否在画布内，不能替代人审。重绘不等于重新证明连续区间最优；其数学依据仍为独立精确候选证书。PDF创建时间、字体与库版本会影响字节，所以不要求重绘PDF与冻结PDF逐字节相等。
