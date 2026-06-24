---
title: LLM-Wiki-Karpathy 摘要
tags: ["LLM", "摘要"]
source: llm-wiki-karpathy.md
date: 2026-06-24
status: published
version: 3
---

# LLM-Wiki-Karpathy 摘要

## 核心主張
- LLM Wiki 的重點不是一次性檢索，而是讓知識持續編譯成可維護的 wiki。
- Raw sources、Wiki、Schema 三層結構把原始資料、編譯後知識與工作規範分開。
- Ingest、Query、Lint 是三個互補流程，分別負責編譯、查詢與維護。
- Index.md 與 log.md 讓 wiki 在中小規模時仍可被持續管理與追蹤。

## 主要章節
### 核心主張
文章主張 LLM 應該把原始來源編譯成持久化 wiki，而不是每次查詢都重新拼湊答案。這種方式讓跨來源的理解、衝突標註與連結維護都能累積下來。

### 三層架構
作者將系統拆成 raw sources、wiki 與 schema 三層：原始資料保持不可變，wiki 存放由 LLM 維護的知識頁，schema 則規範頁面結構與工作流程。

### 主要操作
Ingest 將來源納入 wiki；Query 以 index 找到相關頁再綜合回答；Lint 負責巡檢矛盾、孤兒頁與過時內容，維持整體品質。

### 索引與日誌
Index.md 以主題分類呈現頁面，log.md 則記錄 ingests、queries 與 lint 的時間序，使整個知識庫具有可追蹤的演化歷史。

### 為何有效
LLM 擅長處理重複且細碎的維護工作，因此可以把人從持續整理連結與更新摘要的負擔中解放出來。

## 關鍵概念
| 概念 | 定義 |
|------|------|
| Raw sources | 不可變的原始文件與資料來源。 |
| Wiki | 由 LLM 持續編譯與維護的 Markdown 知識庫。 |
| Schema | 規範頁面格式與工作流程的配置文件。 |
| Ingest | 將新來源讀入、摘要化並加入 wiki 的流程。 |
| Query | 根據問題搜尋 wiki、綜合頁面內容並回答的流程。 |
| Lint | 檢查連結、內容一致性與 frontmatter 的維護流程。 |

## 對本 Wiki 的啟示
- 這個專案應優先維護 raw/inbox、wiki/index.md、wiki/log.md 與 meta.json 的一致性。
- 新增來源時不應只做摘要，還要把相關頁面、索引與歷史記錄一起維護。
- 查詢結果若具有長期價值，應能回寫為新的 wiki 頁面。

## 參考
- 原始來源：llm-wiki-karpathy.md
- raw/inbox/llm-wiki-karpathy.md
- wiki/index.md
- wiki/log.md
