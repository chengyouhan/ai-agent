# Step Scripts（導覽 Agent 主檔 · canonical）

**canonical 路徑**：`peas-agent-core/src/peas_agent/builtin_skills/llm-wiki-coach/references/step-scripts.md`  
Cursor 副本：`~/.cursor/skills/peas-llm-wiki-coach/references/step-scripts.md`（須同步）

**用法**：每則回覆前讀 **當前 `step_id` 整段**，只輸出「學生可見模板」。

**用詞表**：

| 稱呼 | 指誰 |
|------|------|
| 導覽助手 | 帶步驟的對話（Cursor 或右欄，讀 `llm-wiki-coach`） |
| 維護 Agent | 右欄「我的 Agent」，執行 ingest（讀 `llm-wiki` skill） |
| 專案根 | 含 `studio_shell/` 的上一層資料夾 |

---

## Step 1 · step_id: 1

**title**：認識 LLM Wiki

**purpose**：LLM Wiki 不是「上傳檔案就問」的 RAG，而是 Agent **編譯並維持** Markdown 知識庫。三層：`raw/`（你不改舊檔）、`wiki/`（Agent 寫）、`llm-wiki` skill（規則）。共 7 步，一次只做一件事。

**student_action**：若了解，回「開始」。

**completion_phrases**：開始｜好了開始

**if_stuck**：

- **A 和 NotebookLM 差在哪？** → NotebookLM 像每次重找；Wiki 會**累積**在 `wiki/` 裡。
- **B raw 可以改嗎？** → 舊檔不改；新來源你可以**新增**到 `raw/inbox/`。

**agent_must_not**：不得一次列出 Step 2–7 待辦

**學生可見模板**：

```
步驟 1／7 · 認識 LLM Wiki

LLM Wiki 讓 Agent 把讀過的來源「編譯」成 wiki（不是每次重找上傳檔）。三層：raw/（原始）、wiki/（Agent 維護）、llm-wiki skill（規則）。共 7 步。

你要做的事：若了解，回「開始」。

完成後跟我說：「開始」
```

---

## Step 2 · step_id: 2

**title**：建目錄

**purpose**：在**專案根**（`studio_shell/` 的上一層）建立 wiki 骨架。

**student_action**：

1. 建立資料夾：`raw/`、`raw/inbox/`、`raw/assets/`、`wiki/`
2. 建立 `wiki/index.md`，內容至少：`# Wiki 目錄`
3. 建立 `wiki/log.md`，內容至少：`# 變更日誌` 與「僅追加、不刪改歷史」

（可請 Agent 用 write_file，或自己建）

**completion_phrases**：目錄好了｜建好了

**if_stuck**：

- **A 找不到專案根** → 找含 `studio_shell/` 的資料夾，wiki 與 raw 放**同一層**。
- **B 已有 wiki** → 確認四個路徑存在即可，不必重複建。

**學生可見模板**：

```
步驟 2／7 · 建目錄

在專案根（studio_shell 的上一層）建立 wiki 骨架。

你要做的事：
1. 建立 raw/、raw/inbox/、raw/assets/、wiki/
2. 建立 wiki/index.md（標題 # Wiki 目錄）
3. 建立 wiki/log.md（標題 # 變更日誌）

完成後跟我說：「目錄好了」
```

---

## Step 3 · step_id: 3

**title**：開 Obsidian

**purpose**：用 Obsidian 當 wiki 的 IDE（左側 Agent、右側看連結與 graph）。沒 Obsidian 也可略過。

**student_action**：Obsidian →「以資料夾作為 vault 開啟」→ 選**專案根**（不是只選 wiki/）。

**completion_phrases**：Obsidian 好了｜沒裝 Obsidian 用檔案總管

**if_stuck**：

- **A 沒裝 Obsidian** → 用檔案總管能開 `wiki/` 即可；回「沒裝 Obsidian 用檔案總管」算完成。
- **B 只開了 wiki 子資料夾** → 請改開**專案根**，才看得到 raw 與 studio_shell。

**學生可見模板**：

```
步驟 3／7 · 開 Obsidian

用 Obsidian 瀏覽 wiki（選修但推薦）。沒裝也可以。

你要做的事：Obsidian「以資料夾作為 vault 開啟」→ 選專案根（含 studio_shell 的那一層）。

沒 Obsidian 的話，用檔案總管能開 wiki 即可。

完成後跟我說：「Obsidian 好了」或「沒裝 Obsidian 用檔案總管」
```

---

## Step 4 · step_id: 4

**title**：第一份 raw

**purpose**：放第一個**不可被 Agent 改寫**的來源到 raw。

**student_action**：把 Karpathy《LLM Wiki》gist 存成 `raw/inbox/llm-wiki-karpathy.md`

- 來源：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- 可下載 Raw、Web Clipper，或複製 gist 正文存檔

**completion_phrases**：raw 存好了｜gist 存好了

**if_stuck**：

- **A 不會下載** → 瀏覽器開 gist → Raw → 全選複製 → 貼到新檔 `raw/inbox/llm-wiki-karpathy.md`。
- **B 路徑錯** → 必須在**專案根**底下 `raw/inbox/`，不是 wiki/ 裡。

**學生可見模板**：

```
步驟 4／7 · 第一份 raw

第一個來源放 raw（Agent 之後不會改這個檔的內文）。

你要做的事：把 Karpathy LLM Wiki gist 存成 raw/inbox/llm-wiki-karpathy.md

來源：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

完成後跟我說：「raw 存好了」
```

---

## Step 5 · step_id: 5

**title**：第一次 ingest

**purpose**：請**右欄維護 Agent** 讀 `llm-wiki` skill，把 raw 編譯進 wiki（MVP：至少 1 摘要頁 + index + log）。

**student_action**：

1. 開 Agent Studio App，右欄「我的 Agent」
2. **複製下面整段**貼到右欄聊天
3. 等 Agent 完成後，確認 `wiki/` 有新 md、`index.md`、`log.md` 有更新

**copy_paste_block**：

```text
請先 read_file 載入 builtin_skills/llm-wiki/SKILL.md 與 references/ingest.md，然後攝取專案內 raw/inbox/llm-wiki-karpathy.md 進 wiki/：

- 新增至少 1 篇來源摘要 wiki 頁（例如 wiki/LLM-Wiki-Karpathy-摘要.md）
- 更新 wiki/index.md（一條連結 + 一行摘要）
- 在 wiki/log.md 末尾追加 ingest 條目（格式 ## [日期] ingest | llm-wiki-karpathy）

不要修改 raw/ 內任何既有檔案內文。
```

**completion_phrases**：ingest 好了｜wiki 更新了

**if_stuck**：

- **A Agent 說找不到 skill** → 確認 peas-agent-core 已更新到含 `llm-wiki` 內建 skill；重啟 App 或更新 core。
- **B 只有聊天沒寫檔** → 再貼一次 copy_paste_block，要求「實際 write_file 到 wiki/」。
- **C 在 Cursor 貼這段** → ingest **必須在右欄 Agent** 執行，Cursor 不能代替。

**agent_must_not**：不得在本步代替右欄 Agent 完成 ingest（陪練只帶學生貼指令）

**學生可見模板**：

```
步驟 5／7 · 第一次 ingest

要請右欄「我的 Agent」把 raw 編譯進 wiki（不是 Cursor 做）。

你要做的事：
1. 開 Agent Studio，右欄聊天
2. 複製下面整段貼上
3. 確認 wiki 有新頁、index.md 和 log.md 有更新

請先 read_file 載入 builtin_skills/llm-wiki/SKILL.md 與 references/ingest.md，然後攝取專案內 raw/inbox/llm-wiki-karpathy.md 進 wiki/：

- 新增至少 1 篇來源摘要 wiki 頁（例如 wiki/LLM-Wiki-Karpathy-摘要.md）
- 更新 wiki/index.md（一條連結 + 一行摘要）
- 在 wiki/log.md 末尾追加 ingest 條目（格式 ## [日期] ingest | llm-wiki-karpathy）

不要修改 raw/ 內任何既有檔案內文。

完成後跟我說：「ingest 好了」
```

---

## Step 6 · step_id: 6

**title**：看 wiki

**purpose**：親眼確認 wiki 已長出來。

**student_action**：打開 `wiki/index.md`，點進至少一篇新頁，確認有內容且指向 raw 來源。

**completion_phrases**：看得到 wiki｜有摘要頁了

**if_stuck**：

- **A index 是空的** → 回 Step 5 請 Agent 補 index 條目。
- **B Obsidian 看不到** → 用檔案總管開 `wiki/` 也行。

**學生可見模板**：

```
步驟 6／7 · 看 wiki

確認 wiki 真的長出來了。

你要做的事：打開 wiki/index.md，點進至少一篇新摘要頁，確認有內容。

完成後跟我說：「看得到 wiki」
```

---

## Step 7 · step_id: 7

**title**：驗收

**purpose**：逐項確認 MVP；**一次只問一條**。

**驗收問句（依序）**：

1. 專案根有 raw/ 與 wiki/ 嗎？
2. raw/inbox/llm-wiki-karpathy.md 還在嗎？
3. wiki 至少有一篇摘要頁嗎？
4. index.md 有連到那篇嗎？
5. log.md 有 ingest 條目嗎？
6. raw 檔內文沒被 Agent 改過嗎？（目視或 git diff）

**completion_phrases**：全部 OK｜都好了

**if_stuck**：某一項「還沒」→ 只回對應 Step（缺 ingest→5；缺目錄→2）

**agent_must_not**：不得一次列出 6 條填表

**學生可見模板（首次）**：

```
步驟 7／7 · 驗收

逐項確認，一次一項。

你要做的事：專案根有 raw/ 與 wiki/ 嗎？回「OK」或「還沒」。

（後續依驗收問句 2–6 逐條；全部 OK 後請學生說「全部 OK」）
```

---

## Step 7.1 · step_id: 7.1（選修）

**title**：lint

**purpose**：練習 wiki 健檢（非 MVP 必做）。

**student_action**：右欄 Agent 貼：「請 read llm-wiki skill 的 lint.md，對 wiki/ 做 lint，摘要寫入 log.md」

**completion_phrases**：（選修，不阻塞主線）

---

## 步驟順序速查

| step_id | 下一 step_id | 完成句 |
|---------|--------------|--------|
| 1 | 2 | 開始 |
| 2 | 3 | 目錄好了 |
| 3 | 4 | Obsidian 好了 / 沒裝 Obsidian 用檔案總管 |
| 4 | 5 | raw 存好了 |
| 5 | 6 | ingest 好了 |
| 6 | 7 | 看得到 wiki |
| 7 | 結束 | 全部 OK |
