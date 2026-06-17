# Step 7 驗收

一次只問一條；Step 6 剛看過的可直接 OK。

| # | 問句 | 還沒 → |
|---|------|--------|
| 1 | 專案根有 raw/ 與 wiki/ 嗎？ | Step 2 |
| 2 | raw/inbox/llm-wiki-karpathy.md 存在嗎？ | Step 4 |
| 3 | wiki 至少一篇摘要頁嗎？ | Step 5 |
| 4 | index.md 有連到摘要頁嗎？ | Step 5 |
| 5 | log.md 有 ingest 條目嗎？ | Step 5 |
| 6 | raw 內文沒被 Agent 改嗎？ | 提醒 llm-wiki 規則；必要時重做 ingest |

全部 OK → 恭喜完成 LLM Wiki MVP。

選修：Step 7.1 lint（`references/step-scripts.md` §7.1）。
