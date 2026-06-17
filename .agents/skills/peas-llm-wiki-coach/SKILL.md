---
name: peas-llm-wiki-coach
description: 逐步導覽學生建置專案根 LLM Wiki（Karpathy 模式）。導覽 Agent 每則回覆前必讀 references/step-scripts.md 當前 step_id 並照「學生可見模板」輸出；Step 5 須引導學生在 Agent Studio 右欄執行 llm-wiki ingest。與 peas-agent-core 內建 llm-wiki-coach 同等劇本。當使用者提到 peas-llm-wiki-coach、建置 wiki、LLM Wiki 陪練、Karpathy wiki 時使用。
---

# LLM Wiki 建置陪練（peas-llm-wiki-coach · Cursor）

## 何時使用

- 學生在 **Agent Studio 專案根**建 `raw/` + `wiki/`。
- 使用者說「用 peas-llm-wiki-coach 帶我」「建 LLM Wiki」等。
- **同等劇本**：`peas-agent-core` 內建 `llm-wiki-coach`（右欄也可帶同一流程）。

## 核心原則

- **劇本在 `references/step-scripts.md`**（同步自 core canonical，見檔首註）。
- **低能力兜底**：不確定 → 停在本步。
- **Step 5**：ingest **必須**在右欄 Agent 執行；Cursor **不代替** write wiki。

## 執行協定（每則回覆前）

1. **確認 `current_step`**：`1`–`7`（首次 = `1`）。
2. **讀** `references/step-scripts.md` 當步整段。
3. **只輸出**學生可見模板；Step 5 貼 **ingest 指令全文**。
4. 未匹配 `completion_phrases` → 走 `if_stuck`，不得前進。
5. **Step 7**：一次只問一條驗收問句。

## 參考索引

| 檔案 | 用途 |
|------|------|
| `references/step-scripts.md` | **主檔**（與 core 同步） |
| `references/progress-checklist.md` | 進度對照 |
| `references/verification.md` | Step 7 |
| `references/student-journey.md` | 路線圖 |
| `references/optional-query.md` | 選修 |

Wiki 維護規則在 core **`llm-wiki`** skill，非本檔。

## 觸發後第一則

只輸出 Step 1 模板。
