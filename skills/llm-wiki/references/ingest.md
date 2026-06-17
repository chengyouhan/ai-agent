# Ingest — 攝取新來源進 Wiki

## 概述

Ingest 是將原始來源編譯進 wiki 的核心操作。它自動檢測 `second-brain/raw/inbox/` 中的新檔案，產生摘要，更新索引和日誌，並在完成後執行 lint 檢查。

**MVP（最小可行）流程**：
1. 檢測 `second-brain/raw/inbox/` 中的新未處理檔案
2. 讀取原始檔案
3. 產生摘要頁
4. 更新 `second-brain/wiki/index.md`
5. 更新 `second-brain/wiki/log.md`
6. 移檔案至 `second-brain/raw/processed/`
7. 執行 lint（自動）

---

## 觸發方式

### 自動觸發

每次對話開始，自動檢測 `second-brain/raw/inbox/`：

```
檢查 second-brain/raw/inbox/ 是否有新未處理檔案。
若有，提醒使用者：「偵測到 N 個未處理的新檔案。要執行 ingest 嗎？」
```

### 手動觸發

```
請 read_file 載入 skills/llm-wiki/references/ingest.md，
然後根據流程攝取 second-brain/raw/inbox/ 中的新檔案進 second-brain/wiki/
```

---

## 詳細流程

### 第一步：檢測新檔案

**目的**：找出所有未處理的新檔案

**方法**：
1. 列出 `second-brain/raw/inbox/` 所有 `.md` 和 `.txt` 檔案
2. 讀取 `second-brain/wiki/meta.json` 的 `sources` 欄位，取得已處理的檔名列表
3. 篩選出未在列表中的檔案（新檔案）

**輸出**：新檔案列表，例如
```
- second-brain/raw/inbox/file1.md
- second-brain/raw/inbox/file2.txt
```

**限制**：最多一次處理 10 個新檔案（若超過，分批執行）

**進度反饋**：
```
偵測完成：找到 3 個新檔案
- second-brain/raw/inbox/llm-wiki-karpathy.md
- second-brain/raw/inbox/paper-2024.md
- second-brain/raw/inbox/article.txt
是否繼續？（回「繼續」或「停止」）
```

---

### 第二步：讀取和分析

**目的**：理解每個新來源的內容

**方法**：

1. **逐一讀取**每個新檔案的完整內容
2. **識別主要內容**：
   - 標題 / 主題
   - 核心主張或要點
   - 關鍵概念
   - 結構和章節
3. **分類**：判斷內容屬於哪個主題領域

**錯誤處理**：
- 若檔案無法讀取（編碼問題），建立骨架頁面並標記 `status: draft`，提示使用者手動補充
- 若檔案為空或格式不明，記錄警告但繼續

**進度反饋**：
```
正在分析檔案 1/3... [已讀 50%]
檔案類型：摘要
主題分類：LLM 基礎
```

---

### 第三步：產生摘要頁

**目的**：為每個新來源建立 wiki 頁面

**命名規則**：`[來源檔名（去副檔名）]-摘要.md`

例如：
- `second-brain/raw/inbox/llm-wiki-karpathy.md` → `second-brain/wiki/LLM-Wiki-Karpathy-摘要.md`
- `second-brain/raw/inbox/paper-2024.md` → `second-brain/wiki/Paper-2024-摘要.md`

**Frontmatter**：
```yaml
---
title: [來源名] 摘要
tags: [主題標籤, 子標籤]  # 根據內容推斷
source: [原始檔名]
date: [YYYY-MM-DD]  # Ingest 日期
status: published  # 若內容不完整則為 draft
---
```

**摘要內容結構**（遵循 schema.md 的「來源摘要頁」模板）：

1. **核心主張** — 3-5 個核心要點
2. **主要章節** — 按來源結構重新組織，每個章節 1-2 段落
3. **關鍵概念** — 表格列出重要概念
4. **對本 Wiki 的啟示** — 這份來源對 wiki 的貢獻

**摘要品質標準**：
- 長度：500-2000 字（通常 800-1200 字）
- 覆蓋面：涵蓋原文 80% 的重要內容
- 連貫性：邏輯清晰，無碎片化
- 中立性：忠實呈現原文觀點

**進度反饋**：
```
正在產生摘要 2/3...
已產生檔案：second-brain/wiki/Paper-2024-摘要.md (1248 字)
```

---

### 第四步：更新 Index

**目的**：將新摘要加入索引

**檔案**：`second-brain/wiki/index.md`

**方法**：

1. 讀取現有 `second-brain/wiki/index.md`
2. 根據新摘要的主題標籤（tags），判斷應該放在哪個主題章節下
3. **若主題章節已存在**，在該章節新增一行：
   ```markdown
   - [[頁面名-摘要]]：簡短說明（來自來源 X）
   ```
4. **若主題章節不存在**，新增一個主題章節，然後加入連結
5. 保持主題內的頁面順序（按來源名或日期）

**範例**（更新後）：

```markdown
# Wiki 目錄

## LLM 基礎

- [[LLM-Wiki-Karpathy-摘要]] — Karpathy 提出的 LLM Wiki 模式
- [[Paper-2024-摘要]] — 2024 年最新論文

## 其他主題

...
```

**限制**：一次最多新增 10 個主題或 20 條連結

**進度反饋**：
```
正在更新 index...
已新增 2 個主題章節、3 條連結
```

---

### 第五步：更新 Log

**目的**：記錄本次 ingest 的變更

**檔案**：`second-brain/wiki/log.md`

**方法**：

1. 在 `second-brain/wiki/log.md` 最上面（`# 變更日誌` 標題之下）新增一條記錄
2. 格式：`## [YYYY-MM-DD] ingest | [來源簡名]`
3. 若有多個來源，列出所有來源簡名，用逗號分隔
4. 下一行簡述變更內容：新增多少頁、涵蓋哪些主題

**範例**：

```markdown
# 變更日誌

## [2026-06-18] ingest | llm-wiki-karpathy, paper-2024
- 新增摘要頁 2 篇
- 新增主題章節 2 個：LLM 基礎、論文綜合
- 更新 index：3 條新連結

## [2026-06-17] ingest | first-source
...
```

**進度反饋**：
```
正在更新 log...
已記錄本次 ingest
```

---

### 第六步：更新 Meta.json

**目的**：追蹤每個來源的 ingest 歷史

**檔案**：`second-brain/wiki/meta.json`

**方法**：

1. 若 `second-brain/wiki/meta.json` 不存在，建立初始結構（見下方範例）
2. 對每個新來源，在 `sources` 物件中新增或更新一個條目
3. 格式：
   ```json
   "來源檔名（去副檔名）": {
     "filename": "原始檔名.md",
     "first_ingested": "2026-06-17",
     "last_ingested": "2026-06-18",
     "versions": [
       {
         "date": "2026-06-18",
         "pages_created": 1,
         "pages_modified": 0,
         "status": "success"
       }
     ]
   }
   ```
4. 更新 `stats` 欄位中的 `total_pages` 和 `last_ingest_date`

**初始 meta.json 範例**：

```json
{
  "sources": {},
  "stats": {
    "total_pages": 0,
    "total_sources": 0,
    "last_ingest_date": null,
    "last_lint_date": null
  }
}
```

**進度反饋**：
```
正在更新 meta.json...
已記錄 2 個新來源、統計更新
```

---

### 第七步：移檔案至 Processed

**目的**：標記已處理，方便歷史追蹤

**方法**：

1. 確保 `second-brain/raw/processed/` 資料夾存在
2. 將每個已處理的檔案從 `second-brain/raw/inbox/` 移至 `second-brain/raw/processed/[YYYY-MM-DD]/`
   （若日期資料夾不存在則建立）

**範例**：
```
second-brain/raw/inbox/llm-wiki-karpathy.md  →  second-brain/raw/processed/2026-06-18/llm-wiki-karpathy.md
second-brain/raw/inbox/paper-2024.md        →  second-brain/raw/processed/2026-06-18/paper-2024.md
```

**進度反饋**：
```
正在移檔案...
已移 2 個檔案至 second-brain/raw/processed/2026-06-18/
```

---

### 第八步：執行 Lint

**自動觸發**：Ingest 完成後自動執行 lint

**目的**：檢查新增頁面是否有連結錯誤或孤兒頁

**方法**：

1. 讀取 `references/lint.md` 的流程
2. 執行 lint（見 [lint.md](lint.md)）
3. 向使用者展示 lint 報告，請求確認修復

**進度反饋**：
```
Ingest 完成！共處理 2 個來源。
現在執行 lint 檢查...
[lint 結果...]
請確認修復？
```

---

## 錯誤処理與邊界情況

### 情況 1：檔案無法讀取

**症狀**：檔案編碼問題或格式不支持

**處理**：
1. 建立骨架頁面，標題為檔案名
2. 設置 `status: draft`
3. 新增警告提示：
   ```markdown
   > ⚠️ **待手動補充** — 此摘要無法自動生成，請手動編寫內容。
   ```
4. 在 log 中記錄：`[日期] ingest | [來源名] — 失敗（需手動編寫）`

### 情況 2：檔案為空

**症狀**：檔案存在但無內容

**處理**：
1. 跳過該檔案
2. 在 log 中記錄警告
3. 提示使用者檢查檔案

### 情況 3：同一來源多次 Ingest

**症狀**：重複攝取同一個來源

**處理**：
1. 檢查 `meta.json` 中是否已有記錄
2. 若已處理，詢問使用者是否要「替換」或「保留」
3. 若替換：刪除舊摘要頁，建立新的，在 log 中記錄版本更新
4. 若保留：跳過該檔案

### 情況 4：主題判斷失敗

**症狀**：無法自動分類到已有的主題

**處理**：
1. 使用預設主題「其他」或「未分類」
2. 在摘要頁的 frontmatter 中加入 `TODO: 確認主題`
3. 提示使用者手動調整

---

## 驗證清單

Ingest 完成後，檢查以下項目：

- [ ] `raw/inbox/` 中的所有新檔案已處理
- [ ] 為每個新來源建立了摘要頁（`.md` 檔）
- [ ] `wiki/index.md` 已更新，新頁面已加入
- [ ] `wiki/log.md` 已記錄本次操作
- [ ] `wiki/meta.json` 已更新
- [ ] 原檔案已移至 `raw/processed/[日期]/`
- [ ] 所有摘要頁的 frontmatter 完整
- [ ] Lint 已執行並展示結果

---

## 性能考量

- **單次最多處理 10 個檔案**：若超過，自動分批
- **逐一讀取和分析**：避免一次性載入過多數據
- **中間進度反饋**：每處理 1-2 個檔案就提示一次進度

---

## 使用範例

### 範例 1：首次 Ingest

**用戶輸入**：
```
請執行 ingest，攝取 raw/inbox/ 中的新檔案
```

**Agent 回應**：
```
檢查中...
偵測到 1 個新檔案：
- raw/inbox/llm-wiki-karpathy.md

開始 ingest...
✓ 已產生摘要頁：wiki/LLM-Wiki-Karpathy-摘要.md (1248 字)
✓ 已更新 index：新增「LLM 基礎」主題
✓ 已更新 log：新增 ingest 記錄
✓ 已移檔案至 raw/processed/2026-06-18/

正在執行 lint...
[lint 報告...]

Ingest 完成！
```

### 範例 2：多檔案 Ingest

**用戶輸入**：
```
幫我攝取所有新來源
```

**Agent 回應**：
```
檢查中...
偵測到 3 個新檔案：
1. raw/inbox/paper-2024.md
2. raw/inbox/article.txt
3. raw/inbox/guide.md

開始 ingest...
正在分析檔案 1/3... [已完成 33%]
✓ 已產生：wiki/Paper-2024-摘要.md

正在分析檔案 2/3... [已完成 66%]
✓ 已產生：wiki/Article-摘要.md

正在分析檔案 3/3... [已完成 100%]
✓ 已產生：wiki/Guide-摘要.md

正在更新 index...
✓ 新增 3 個主題章節

正在執行 lint...
[lint 報告...]

Ingest 完成！處理了 3 個新檔案。
```

---

## 常見問題

**Q: Ingest 是否會修改 raw/inbox/ 中的原檔？**  
A: 不會。只會讀取內容，完成後移檔案至 `raw/processed/` 以標記已處理。

**Q: 可以重複 ingest 同一個來源嗎？**  
A: 可以。若要替換舊摘要，會詢問確認。舊版本在 log 和 meta.json 中記錄。

**Q: 如果摘要不滿意怎麼辦？**  
A: 可以手動編輯 wiki 中的摘要頁，或者刪除後重新 ingest。

**Q: 摘要篇幅有限制嗎？**  
A: 建議 500-2000 字。無硬性上限，但過長可能難以維護。

---

**版本**：1.0（2026-06-17）  
**狀態**：MVP - 優先實現  
**關聯**：[schema.md](schema.md) • [lint.md](lint.md)
