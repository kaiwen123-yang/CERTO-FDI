# Independent Adversarial Review Prompt

你是独立 T-RO 审稿人、系统综述审计员和公共基准复现审计员。不要假设当前候选方法正确或新颖。

## Literature

- 复核搜索数据库、检索式、去重、筛选和全文数量；
- 随机抽查至少 15 张 method cards 与原文页码；
- 检查 abstract-only 文献是否被错误用于开放结论；
- 独立寻找 killer papers；
- 检查“没有单篇同时包含全部模块”的组合创新谬误；
- 复核 2025–2026 正式/预印本状态。

## Datasets

- 校验官方版本、许可、checksum、schema 和 split；
- 检查窗口/episode 泄漏；
- 检查是否伪造缺失 URDF、惯性、力矩或控制信号；
- 检查异常标签是否参与阈值/模型选择。

## Baselines

- 复现至少一个 dataset-native baseline；
- 审计官方代码 commit 和 patch；
- 检查复现等级是否诚实；
- 重新计算主指标；
- 检查参数预算、搜索预算和 seeds。

## Candidate

- 判断 chain/geometry 增量是否在至少两个公共数据集稳定；
- 判断增量是否只是 anomaly head、数据清洗或额外输入；
- 检查公共数据不足时是否仍然强行使用 physics claims；
- 将自建仿真和公共证据严格分开。

## Final

独立返回一个组合终态，并列出任何会改变结论的 plausible bug、漏检文献或替代 split。
