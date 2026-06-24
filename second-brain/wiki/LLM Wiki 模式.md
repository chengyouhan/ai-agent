---
title: LLM Wiki 模式
tags: ["wiki", "draft"]
source: Manual
date: 2026-06-24
status: published
version: 1
---

# LLM Wiki 模式

## 定義

LLM Wiki 模式是由 Andrej Karpathy 提出的一種知識管理方法：把原始資料持續編譯成可維護的 Markdown 知識庫，而不是每次查詢都重新檢索原始文件。

## 核心要素

### 三層架構
- **Raw sources**：不可變的原始文件與資料來源。
- **Wiki**：由 LLM 持續編譯與維護的 Markdown 知識庫。
- **Schema**：規範頁面格式與工作流程的配置文件。

### 三個互補流程
- **Ingest**：將新來源讀入、摘要化並加入 wiki。
- **Query**：根據問題搜尋 wiki、綜合頁面內容並回答。
- **Lint**：檢查連結、內容一致性與 frontmatter 的維護流程。

## 與 Markdown Wiki 的差別

| 面向 | Markdown Wiki | LLM Wiki |
|------|---------------|----------|
| 主要讀者 | 人類 | 人類 + LLM / Agent |
| 重點 | 可讀性、導覽、章節結構 | 可檢索、可引用、主題單一、來源可追溯 |
| 維護方式 | 人工為主 | LLM 持續協助整理與維護 |

## 與 Agent 上下文的差別

Agent 上下文是給 Agent 直接工作用的濃縮背景；LLM Wiki 則是長期累積、結構化的知識庫。兩者可以互補：Agent 上下文常從 LLM Wiki 中萃取而來。

## 實踐應用

- 累積跨來源的綜合理解
- 減少重複回答同一問題的計算成本
- 讓知識演化過程可追蹤、可審核

## 常見誤區

- 誤區 1：把 LLM Wiki 當成一次性摘要。它應該是持續維護的知識庫。
- 誤區 2：忽略來源追溯。每個頁面都應該記錄來源與版本。

## 相關頁面
- [[index.md]]
- [[LLM-Wiki-Karpathy-摘要.md]]
