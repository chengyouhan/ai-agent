---
title: Obsidian 教學
tags: ["Obsidian", "LLM Wiki", "概念"]
source: llm-wiki-karpathy.md
date: 2026-06-24
status: published
version: 1
---

# Obsidian 教學

## 定義

Obsidian 教學在此指「以 Obsidian 作為 LLM Wiki 的閱讀與維護介面」的實作概念。根據 Karpathy 的 LLM Wiki 模式，Obsidian 不僅是筆記軟體，更是 wiki 的「整合開發環境（IDE）」：LLM 負責編寫與維護 Markdown 頁面，人類則在 Obsidian 中瀏覽連結、檢視圖譜、確認更新結果。

## 核心要素

### 雙視窗工作流

Karpathy 建議的實際操作方式，是將 LLM Agent 與 Obsidian 並排放置：

- **一側是 LLM Agent**：負責讀取來源、撰寫摘要、更新概念頁、維護索引與日誌。
- **一側是 Obsidian**：即時顯示 wiki 資料夾中的 Markdown 檔案，讓使用者追蹤連結與圖譜變化。

這種分工讓「知識編譯」與「知識閱讀」同步進行，減少來回切換的成本。

### Markdown 作為通用格式

Obsidian 原生支援 Markdown，因此 LLM 產出的 wiki 頁面可直接被 Obsidian 讀取，無需額外轉換。配合 YAML frontmatter，還能讓 Obsidian 外掛（如 Dataview）依標籤、日期、來源等欄位產生動態列表。

### 連結與圖譜視覺化

Obsidian 的雙向連結語法 `[[頁面名稱]]` 與 LLM Wiki 的互連性需求高度契合。其圖譜視圖（Graph View）可幫助使用者：

- 識別知識樞紐頁面
- 發現孤兒頁面
- 視覺化概念之間的關聯強度

### 外掛生態擴充

Karpathy 在來源中特別提到幾個可強化 LLM Wiki 的 Obsidian 外掛與工具：

| 工具 | 用途 |
|------|------|
| Obsidian Web Clipper | 將網頁文章轉為 Markdown，快速收入 raw sources |
| 附件下載熱鍵 | 把文章中的圖片下載到本地 `raw/assets/`，避免連結失效 |
| Graph View | 視覺化 wiki 的連結結構 |
| Marp | 將 wiki 內容轉為簡報投影片 |
| Dataview | 依 frontmatter 欄位產生動態查詢與表格 |

## 實踐應用

- **個人知識管理**：將日記、文章、播客筆記逐步編譯成結構化 wiki。
- **研究主題深耕**：長期追蹤某領域論文與報告，讓綜合理解持續累積。
- **團隊內部 wiki**：由 LLM 維護會議紀錄、專案文件與客戶通話摘要。
- **書籍閱讀伴侶**：為角色、主題、情節線建立互連頁面，形成個人版「粉絲 wiki」。

## 常見誤區

- **誤區 1：把 Obsidian 當成純筆記本**。在 LLM Wiki 模式中，Obsidian 更像是「知識庫的 IDE」，重點在於連結結構與可維護性，而非單純收集片段。
- **誤區 2：忽略本地附件管理**。若圖片仍使用外部 URL，來源失效後 LLM 將無法再參考這些視覺資訊，建議設定固定附件資料夾並綁定下載熱鍵。
- **誤區 3：讓 LLM 獨自維護而不檢查**。雖然 LLM 能批量更新多個頁面，但人類仍需負責審核關鍵連結、確認衝突標註是否合理。

## 相關頁面

- [[LLM Wiki 模式]]
- [[LLM-Wiki-Karpathy-摘要]]
- [[index.md]]
