# Figure caption and visual review

**Figure. Memory benefit after paying the same homogeneous settling requirement.** The common scalar plant has innovation variance q and a known force input; kappa is the dimensionless constant-input missing-span penalty (actual coefficient beta=kappa/q). For c∈[.8,.95], the qualification uses E=1, epsilon=.81, no extra move slots, and the smallest positive integer s with c^s≤.81; k=s. (a) The fixed-k=1 penalty decreases smoothly, whereas the qualified penalty has downward segments and upward right-side jumps. The black square marks the exact continuum minimum at c=81/100, kappa=361/16561. (b) The same qualification determines the excluded-slot count. Filled right endpoints belong to the shorter k; hollow left endpoints show unattained right limits. Irrational endpoint positions are rounded only for display. The exact three-point family {.8,.9,.95} instead has its best member at .9; the full-interval ranking comes from rational candidate certificates, not curve resolution. These are analytical curves with no random observations or confidence intervals. The qualification constrains only the homogeneous component and does not certify full noisy/forced return, nonlinear tracking or actuator feasibility.

来源：`controller_settling_tradeoff_v1.md`、`controller_settling_checks_v1.json`；derived CSV为1202行/两个601点组，没有缺值。profile脚本把字符串mode标成unknown，本图语义手工确定为两种解析协议类别，k为整数序数；不进行统计离群点过滤。

视觉复查：首版标题与(b)编号重叠、标注压蓝线，机器未发现但人工读图发现；已分开全局标题和编号，并移走跨曲线箭头，重渲染。最终彩色与灰度检查均无缺字、裁切、图例压数据、文本重叠或子图对齐问题；短k=5区间如实很窄，完整端点值以精确表为准。最低字体8pt，7.16×3.1in，600dpi位图、PDF/SVG矢量。未把这张图标记为实机验证。

格式检查：SVG与600dpi PNG通过strict checker。其PDF字体检查仅查看Type0父字体而给出未嵌入WARN；另用pypdf读取全部四个实际DescendantFonts/FontDescriptor，均含嵌入font stream，且无Type3。因此保留原WARN记录并以实际descendant检查解释，不声称原checker全PASS。
