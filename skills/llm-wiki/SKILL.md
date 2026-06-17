---
name: llm-wiki
description: This skill supports maintaining and querying a persistent LLM Wiki based on the Karpathy model. It provides three core operations—Ingest (auto-detecting and compiling new sources), Query (searching and synthesizing answers from wiki pages), and Lint (maintaining wiki quality by detecting and fixing issues). Use this skill when building and maintaining a cumulative knowledge base where AI continuously compiles Markdown content from raw sources, enabling cross-source synthesis and persistent knowledge accumulation.
---

# LLM Wiki Skill

## Purpose

This skill enables maintaining a persistent, continuously-evolving knowledge base (wiki) that compiles raw sources into structured Markdown pages. Rather than retrieving from original documents each time, the wiki approach lets AI agents persistently maintain and update an accumulated knowledge base where insights can be synthesized across sources and interconnected.

**Three-layer architecture:**
- **Raw sources** (`second-brain/raw/inbox/`) — Immutable original documents
- **Wiki** (`second-brain/wiki/`) — AI-maintained Markdown knowledge base
- **Schema** (`references/schema.md`) — Standards and templates

## When to Use This Skill

- To build and maintain a knowledge base that accumulates new sources over time
- When synthesis across multiple sources should be persisted rather than re-computed
- To organize domain knowledge in a queryable, interconnected wiki structure
- When wiki quality needs ongoing maintenance (detecting dead links, orphaned pages, contradictions)

## Core Operations

### Ingest — Compile New Sources into Wiki

**Trigger:**
```
Read skills/llm-wiki/references/ingest.md, 
then ingest new files from raw/inbox/ into wiki/
```

**Workflow:**
1. Auto-detect new unprocessed files in `second-brain/raw/inbox/` (max 10 per run)
2. Generate summary pages following naming: `[source-name]-摘要.md`
3. Update `second-brain/wiki/index.md` (add links by topic), `second-brain/wiki/log.md` (record changes), `second-brain/wiki/meta.json` (track history)
4. Move processed files to `second-brain/raw/processed/[date]/`
5. Auto-run lint to verify quality

**References:** [ingest.md](references/ingest.md)

---

### Query — Search Wiki and Synthesize Answers

**Trigger:**
```
Read skills/llm-wiki/references/query.md,
then search wiki/index.md for relevant pages and synthesize an answer
```

**Workflow:**
1. Extract question intent and keywords
2. Search `second-brain/wiki/index.md` for related pages (max 5)
3. Read pages and synthesize analysis
4. Show results and offer to save new analysis as wiki page (user confirms)
5. If no relevant pages exist, propose creating new page skeleton

**Key constraint:** Do not auto-create new pages; user must confirm.

**References:** [query.md](references/query.md)

---

### Lint — Maintain Wiki Quality

**Trigger:**
```
Read skills/llm-wiki/references/lint.md,
then scan wiki/ for errors and auto-fix issues (max 5 per run)
```

**Workflow:**
1. Scan `second-brain/wiki/` structure and frontmatter completeness
2. Check network errors (dead links, orphan pages, unindexed pages)
3. Check content consistency (outdated statements, conflicts, TODOs)
4. Auto-repair where safe (add backlinks, fix frontmatter, infer tags)
5. Generate Markdown list report and request user confirmation

**Auto-triggered:** After every ingest completion.

**References:** [lint.md](references/lint.md)

---

## Directory Structure

```
project-root/
├── second-brain/                  # LLM Wiki workspace
│   ├── raw/                       # Immutable raw sources
│   │   ├── inbox/                 # New files awaiting ingest
│   │   ├── processed/             # Ingested files (archive)
│   │   └── assets/                # Images, PDFs, etc.
│   ├── wiki/                      # Compiled wiki
│   │   ├── index.md               # Topic-organized index
│   │   ├── log.md                 # Change log
│   │   ├── meta.json              # Ingest history
│   │   ├── [source]-摘要.md       # Summary pages
│   │   └── [concept].md           # Concept, entity, workflow pages
│   └── .obsidian/                 # Obsidian vault config (optional)
└── skills/llm-wiki/
    ├── SKILL.md                   # This file
    └── references/
        ├── schema.md              # Page templates, frontmatter spec, quality checklist
        ├── ingest.md              # Detailed ingest workflow + examples
        ├── query.md               # Detailed query workflow + edge cases
        └── lint.md                # Detailed lint workflow + repair rules
```

---

## Getting Started

**First time:**
1. Confirm directory structure exists (`second-brain/raw/inbox/`, `second-brain/wiki/`, `second-brain/raw/processed/`)
2. Place first source in `second-brain/raw/inbox/`
3. Trigger: "Ingest new sources"

**Regular use:**
- Add new sources to `second-brain/raw/inbox/`
- Ask questions to query wiki
- Run lint periodically to check health

---

## Key Constraints

| Item | Limit | Reason |
|------|-------|--------|
| Files per ingest | 10 max | Context management |
| Pages per query | 5 max | Synthesis quality |
| Fixes per lint | 5 max | Safety; user reviews |
| Summary length | 500-2000 words | Maintainability |

---

## Configuration Defaults

- **Auto-detect ingest** — Enabled (checks `second-brain/raw/inbox/` each turn)
- **Auto-lint after ingest** — Enabled (requires user confirmation to apply fixes)
- **Progress feedback** — Enabled (shows percentages during long operations)
- **Error handling** — Tolerant (creates skeleton pages if parsing fails; prompts user to fill)

---

## Workflow Examples

**Example 1: First Ingest**
```
User: Ingest new sources
Agent: Reads ingest.md, detects llm-wiki-karpathy.md in second-brain/raw/inbox/
       → Generates second-brain/wiki/LLM-Wiki-Karpathy-摘要.md
       → Updates second-brain/wiki/index.md with "LLM Basics" section
       → Runs lint and reports: "Ingest complete; no issues found"
```

**Example 2: Query**
```
User: What is the three-layer wiki architecture?
Agent: Reads query.md, searches index.md
       → Finds [[LLM-Wiki-Karpathy-摘要]]
       → Reads page and synthesizes answer with citations
       → Offers: "Save this as new 'Wiki Architecture' page?"
```

**Example 3: Lint After Ingest**
```
Agent auto-runs lint after ingest
     → Detects 1 orphan page
     → Adds 2 backlinks auto-magically
     → Flags 1 dead link (needs user confirmation)
     → Report: "Fixed 2 items; 1 needs review"
```

---

## FAQ

**Q: Why separate raw/ and wiki/?**  
A: Preserving raw sources allows re-processing and auditing. Wiki is AI's compiled artifact and can be regenerated.

**Q: Can Query auto-save analysis to wiki?**  
A: No. Only display results; user must confirm before saving as new page.

**Q: Multiple ingests of same source?**  
A: Replaces old summary; version history recorded in log and meta.json; old version in raw/processed/.

**Q: Does Lint delete pages?**  
A: No. Only marks and proposes fixes; user must approve.

---

## References

- [schema.md](references/schema.md) — Frontmatter spec, page templates, quality checklist
- [ingest.md](references/ingest.md) — Step-by-step ingest workflow, error handling, examples
- [query.md](references/query.md) — Query workflow, context management, edge cases
- [lint.md](references/lint.md) — Lint checks, repair rules, report format

---

**Version:** 1.0 (2026-06-17) | **Based on:** Karpathy LLM Wiki Model | **Status:** MVP Ready
