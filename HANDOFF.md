# 导航 web_search 评测：进度交接

更新：2026-10-22

## 目标
在 qwen-plus-character / qwen3.7-flash 中选型，并通过 SP 优化减少"web_search 给的地点高德接不住"。测试接口：`/test/online-web-search`（内网，可传 model 和 systemPrompt），本地用 Fuyao Coding 跑批。

## 已完成
| 轮次 | SP | 状态 | 关键结果 |
|---|---|---|---|
| A | 不传（plus 默认配置已近似带线上 SP） | 完成 | 通过率 plus 82.4% / flash 76.4% |
| B | 线上 SP | 完成 | 通过率 plus 83.9% / flash 80.6%；改名/旧名、多入口无改善 |
| C | `C轮_SP_v3.txt`（新增地点规则） | 完成 | 通过率 plus 74.8% / flash 77.8%，变差；主因“查不到只回固定话术”误伤 18 条 |
| D | `C轮_SP_v4.txt`（修正 v3 误伤） | 待跑 | 先复测 C 轮变化的 68 条 |

## 仓库文件
- `run_eval.py`：跑批脚本
- `testsets/merged_nav_136.csv`：合并测试集（新增 41 + 旧集 95，含 7 家旧回答）
- `testsets/review_notes_round1.md`、`testsets/gaode_check_round1.md`：复核意见、高德人工复核
- `reports/导航websearch评测汇总.docx`：第一轮报告
- `reports/线上SP效果AB对比.docx`：A/B 报告
- `reports/SP三轮迭代评测ABC.docx`：A/B/C 报告
- `reports/charts/`：报告用图

SP 原文（线上版、C 轮 v3）为内部提示词，未放入仓库，在用户本地 `本地集子跑批` 文件夹。

## 下一步
1. 用户用 v4 复测 68 条，再跑全量
2. 线上维持 B 轮 SP
3. 待办：研发确认日期注入、高德存在性校验；重点 query 重复 3～5 次
