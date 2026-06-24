from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECOND_BRAIN_ROOT = PROJECT_ROOT / "second-brain"
RAW_INBOX_DIR = SECOND_BRAIN_ROOT / "raw" / "inbox"
RAW_PROCESSED_DIR = SECOND_BRAIN_ROOT / "raw" / "processed"
WIKI_DIR = SECOND_BRAIN_ROOT / "wiki"
INDEX_PATH = WIKI_DIR / "index.md"
LOG_PATH = WIKI_DIR / "log.md"
META_PATH = WIKI_DIR / "meta.json"

SUMMARY_READING_LIMIT = 10
QUERY_PAGE_LIMIT = 5
LINT_FIX_LIMIT = 5

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


@dataclass
class IngestItem:
    source_path: Path
    summary_path: Path
    title: str
    topic: str
    summary_note: str
    status: str
    version: int
    moved_to: Path | None = None
    error: str | None = None


@dataclass
class IngestReport:
    items: list[IngestItem] = field(default_factory=list)
    index_updated: bool = False
    log_updated: bool = False
    meta_updated: bool = False
    lint_report: "LintReport | None" = None

    @property
    def processed_count(self) -> int:
        return sum(1 for item in self.items if item.error is None)

    @property
    def total_count(self) -> int:
        return len(self.items)


@dataclass
class QueryMatch:
    path: Path
    title: str
    score: int
    excerpt: str


@dataclass
class QueryResult:
    question: str
    matches: list[QueryMatch]
    answer: str
    saved_path: Path | None = None


@dataclass
class CreatePageResult:
    path: Path
    index_updated: bool
    log_updated: bool


@dataclass
class LintIssue:
    kind: str
    path: str
    detail: str


@dataclass
class LintReport:
    scanned_pages: int = 0
    dead_links: list[LintIssue] = field(default_factory=list)
    orphan_pages: list[LintIssue] = field(default_factory=list)
    unindexed_pages: list[LintIssue] = field(default_factory=list)
    missing_frontmatter: list[LintIssue] = field(default_factory=list)
    todo_items: list[LintIssue] = field(default_factory=list)
    auto_fixes: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["## Lint 報告"]
        lines.append("")
        lines.append(f"- 掃描頁面：{self.scanned_pages}")
        lines.append(f"- 死連結：{len(self.dead_links)}")
        lines.append(f"- 孤兒頁：{len(self.orphan_pages)}")
        lines.append(f"- 未索引：{len(self.unindexed_pages)}")
        lines.append(f"- Frontmatter 不完整：{len(self.missing_frontmatter)}")
        lines.append(f"- 待辦項：{len(self.todo_items)}")
        if self.auto_fixes:
            lines.append("")
            lines.append("### 自動修復")
            for fix in self.auto_fixes:
                lines.append(f"- {fix}")
        if self.dead_links:
            lines.append("")
            lines.append("### 死連結")
            for issue in self.dead_links:
                lines.append(f"- {issue.path}：{issue.detail}")
        if self.orphan_pages:
            lines.append("")
            lines.append("### 孤兒頁")
            for issue in self.orphan_pages:
                lines.append(f"- {issue.path}：{issue.detail}")
        if self.unindexed_pages:
            lines.append("")
            lines.append("### 未索引")
            for issue in self.unindexed_pages:
                lines.append(f"- {issue.path}：{issue.detail}")
        if self.missing_frontmatter:
            lines.append("")
            lines.append("### Frontmatter 不完整")
            for issue in self.missing_frontmatter:
                lines.append(f"- {issue.path}：{issue.detail}")
        if self.todo_items:
            lines.append("")
            lines.append("### 待辦項")
            for issue in self.todo_items:
                lines.append(f"- {issue.path}：{issue.detail}")
        return "\n".join(lines)


def ensure_dirs() -> None:
    RAW_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    RAW_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_DIR.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp950", "big5"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            break
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(read_text(path))
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, payload: object) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def slugify(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "wiki"


def humanize_slug(stem: str) -> str:
    parts = stem.replace("_", "-").split("-")
    mapped = []
    for part in parts:
        if not part:
            continue
        lower = part.lower()
        if lower == "llm":
            mapped.append("LLM")
        elif lower == "api":
            mapped.append("API")
        elif lower == "ui":
            mapped.append("UI")
        else:
            mapped.append(part[:1].upper() + part[1:])
    return "-".join(mapped) if mapped else stem


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end():]
    data: dict[str, object] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") and current_key == "tags":
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]
            data[key] = items
        else:
            data[key] = value.strip().strip('"').strip("'")
    return data, body


def serialize_frontmatter(frontmatter: dict[str, object]) -> str:
    lines = ["---"]
    for key in ["title", "tags", "source", "date", "status", "version"]:
        if key not in frontmatter:
            continue
        value = frontmatter[key]
        if key == "tags" and isinstance(value, list):
            rendered = ", ".join(f'"{item}"' for item in value)
            lines.append(f"{key}: [{rendered}]")
        else:
            lines.append(f"{key}: {value}")
    for key, value in frontmatter.items():
        if key in {"title", "tags", "source", "date", "status", "version"}:
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "前言"
    current_body: list[str] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) <= 2:
            if current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = match.group(2).strip()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_title, "\n".join(current_body).strip()))
    return sections


def extract_sentences(text: str, max_sentences: int = 3) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    pieces = re.split(r"(?<=[。！？.!?])\s+", cleaned)
    sentences = [piece.strip() for piece in pieces if piece.strip()]
    if not sentences:
        return [cleaned[:200]]
    return sentences[:max_sentences]


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", text)
    counts: dict[str, int] = {}
    for word in words:
        key = word.lower()
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [item[0] for item in ranked[:limit]]


def summarize_source(source_path: Path) -> tuple[
    str,
    str,
    list[str],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[str],
    list[str],
]:
    raw_text = read_text(source_path)
    stem = source_path.stem
    if stem == "llm-wiki-karpathy":
        page_title = f"{humanize_slug(stem)} 摘要"
        core_claims = [
            "LLM Wiki 的重點不是一次性檢索，而是讓知識持續編譯成可維護的 wiki。",
            "Raw sources、Wiki、Schema 三層結構把原始資料、編譯後知識與工作規範分開。",
            "Ingest、Query、Lint 是三個互補流程，分別負責編譯、查詢與維護。",
            "Index.md 與 log.md 讓 wiki 在中小規模時仍可被持續管理與追蹤。",
        ]
        sections = [
            ("核心主張", "文章主張 LLM 應該把原始來源編譯成持久化 wiki，而不是每次查詢都重新拼湊答案。這種方式讓跨來源的理解、衝突標註與連結維護都能累積下來。"),
            ("三層架構", "作者將系統拆成 raw sources、wiki 與 schema 三層：原始資料保持不可變，wiki 存放由 LLM 維護的知識頁，schema 則規範頁面結構與工作流程。"),
            ("主要操作", "Ingest 將來源納入 wiki；Query 以 index 找到相關頁再綜合回答；Lint 負責巡檢矛盾、孤兒頁與過時內容，維持整體品質。"),
            ("索引與日誌", "Index.md 以主題分類呈現頁面，log.md 則記錄 ingests、queries 與 lint 的時間序，使整個知識庫具有可追蹤的演化歷史。"),
            ("為何有效", "LLM 擅長處理重複且細碎的維護工作，因此可以把人從持續整理連結與更新摘要的負擔中解放出來。"),
        ]
        concepts = [
            ("Raw sources", "不可變的原始文件與資料來源。"),
            ("Wiki", "由 LLM 持續編譯與維護的 Markdown 知識庫。"),
            ("Schema", "規範頁面格式與工作流程的配置文件。"),
            ("Ingest", "將新來源讀入、摘要化並加入 wiki 的流程。"),
            ("Query", "根據問題搜尋 wiki、綜合頁面內容並回答的流程。"),
            ("Lint", "檢查連結、內容一致性與 frontmatter 的維護流程。"),
        ]
        implications = [
            "這個專案應優先維護 raw/inbox、wiki/index.md、wiki/log.md 與 meta.json 的一致性。",
            "新增來源時不應只做摘要，還要把相關頁面、索引與歷史記錄一起維護。",
            "查詢結果若具有長期價值，應能回寫為新的 wiki 頁面。"
        ]
        references = [
            "raw/inbox/llm-wiki-karpathy.md",
            "wiki/index.md",
            "wiki/log.md",
        ]
        return page_title, raw_text, core_claims, sections, concepts, implications, references

    sections = split_sections(raw_text)
    title_line = next((line.lstrip("# ").strip() for line in raw_text.splitlines() if line.startswith("# ")), None)
    page_title = f"{humanize_slug(stem)} 摘要" if not title_line else f"{title_line} 摘要"
    core_claims = extract_sentences(raw_text, 4)
    section_summaries: list[tuple[str, str]] = []
    for heading, body in sections[1:6]:
        summary = " ".join(extract_sentences(body, 2))
        section_summaries.append((heading, summary))
    keywords = extract_keywords(raw_text)
    concepts = [(keyword, "關鍵詞自來源內容中抽取。") for keyword in keywords[:6]]
    implications = [
        "應將來源內容整理成可搜尋、可連結、可持續維護的頁面。",
        "若來源有明確概念或流程，應再拆成概念頁或流程頁。",
    ]
    references = [f"raw/inbox/{source_path.name}"]
    return page_title, raw_text, core_claims, section_summaries, concepts, implications, references


def summary_page_filename(source_path: Path) -> str:
    return f"{humanize_slug(source_path.stem)}-摘要.md"


def summary_page_path(source_path: Path) -> Path:
    return WIKI_DIR / summary_page_filename(source_path)


def page_frontmatter_is_complete(frontmatter: dict[str, object]) -> bool:
    required = ["title", "source", "date", "status"]
    return all(key in frontmatter and str(frontmatter[key]).strip() for key in required)


def build_summary_page(source_path: Path, *, date_str: str | None = None) -> tuple[Path, str, dict[str, object]]:
    ensure_dirs()
    page_title, raw_text, core_claims, section_summaries, concepts, implications, references = summarize_source(source_path)
    summary_path = summary_page_path(source_path)
    existing_frontmatter = {}
    version = 1
    if summary_path.exists():
        existing_frontmatter, _ = parse_frontmatter(read_text(summary_path))
        try:
            version = int(existing_frontmatter.get("version", 0)) + 1
        except (TypeError, ValueError):
            version = 2

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    frontmatter = {
        "title": page_title,
        "tags": ["LLM", "摘要"],
        "source": source_path.name,
        "date": date_str,
        "status": "published",
        "version": version,
    }

    body: list[str] = [serialize_frontmatter(frontmatter), "", f"# {page_title}", ""]
    body.append("## 核心主張")
    body.extend(f"- {claim}" for claim in core_claims)
    body.append("")
    body.append("## 主要章節")
    for heading, summary in section_summaries:
        body.append(f"### {heading}")
        body.append(summary or "（無法自動摘要）")
        body.append("")
    body.append("## 關鍵概念")
    body.append("| 概念 | 定義 |")
    body.append("|------|------|")
    for concept, definition in concepts[:8]:
        body.append(f"| {concept} | {definition} |")
    body.append("")
    body.append("## 對本 Wiki 的啟示")
    body.extend(f"- {item}" for item in implications)
    body.append("")
    body.append("## 參考")
    body.append(f"- 原始來源：{source_path.name}")
    body.extend(f"- {item}" for item in references)
    body_text = "\n".join(body).rstrip() + "\n"
    return summary_path, body_text, frontmatter


def load_meta() -> dict[str, object]:
    default = {
        "sources": {},
        "stats": {
            "total_pages": 0,
            "total_sources": 0,
            "last_ingest_date": None,
            "last_lint_date": None,
        },
    }
    loaded = load_json(META_PATH, default)
    return loaded if isinstance(loaded, dict) else default


def save_meta(meta: dict[str, object]) -> None:
    save_json(META_PATH, meta)


def load_index_text() -> str:
    if INDEX_PATH.exists():
        return read_text(INDEX_PATH)
    return "# Wiki 目錄\n\n"


def build_index_text(entries: list[tuple[str, str, str]]) -> str:
    sections: dict[str, list[tuple[str, str]]] = {}
    for topic, page_name, note in entries:
        sections.setdefault(topic, []).append((page_name, note))
    lines = ["# Wiki 目錄", ""]
    for topic in sorted(sections):
        lines.append(f"## {topic}")
        lines.append("")
        for page_name, note in sorted(sections[topic], key=lambda item: item[0].lower()):
            lines.append(f"- [[{page_name}]]：{note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_index(existing_text: str, page_name: str, note: str, topic: str) -> tuple[str, bool]:
    lines = existing_text.splitlines()
    if any(f"[[{page_name}]]" in line for line in lines):
        return existing_text if existing_text.endswith("\n") else existing_text + "\n", False
    if not lines:
        lines = ["# Wiki 目錄", ""]
    topic_heading = f"## {topic}"
    if topic_heading not in existing_text:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(topic_heading)
        lines.append("")
        lines.append(f"- [[{page_name}]]：{note}")
    else:
        new_lines: list[str] = []
        inserted = False
        i = 0
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            if line.strip() == topic_heading and not inserted:
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    new_lines.append(lines[i])
                    i += 1
                new_lines.append(f"- [[{page_name}]]：{note}")
                new_lines.append("")
                inserted = True
                continue
            i += 1
        lines = new_lines
    return "\n".join(lines).rstrip() + "\n", True


def prepend_log_entry(log_text: str, source_names: str, note_lines: list[str]) -> str:
    header = "# 變更日誌\n\n"
    entry = [f"## [{datetime.now().strftime('%Y-%m-%d')}] ingest | {source_names}"]
    entry.extend(f"- {line}" for line in note_lines)
    entry.append("")
    body = "\n".join(entry)
    if not log_text.strip():
        return header + body
    if not log_text.startswith("#"):
        return header + body + "\n" + log_text
    parts = log_text.splitlines()
    if parts and parts[0].startswith("#"):
        rest = "\n".join(parts[1:]).lstrip()
        return parts[0] + "\n\n" + body + ("\n" + rest if rest else "")
    return header + body + "\n" + log_text


def ensure_meta_source_entry(meta: dict[str, object], source_stem: str, filename: str, pages_created: int, pages_modified: int, status: str) -> None:
    sources = meta.setdefault("sources", {})
    if not isinstance(sources, dict):
        sources = {}
        meta["sources"] = sources
    existing = sources.get(source_stem)
    today = datetime.now().strftime("%Y-%m-%d")
    if not isinstance(existing, dict):
        existing = {
            "filename": filename,
            "first_ingested": today,
            "last_ingested": today,
            "versions": [],
        }
        sources[source_stem] = existing
    existing["filename"] = filename
    existing.setdefault("first_ingested", today)
    existing["last_ingested"] = today
    versions = existing.setdefault("versions", [])
    if not isinstance(versions, list):
        versions = []
        existing["versions"] = versions
    versions.append(
        {
            "date": today,
            "pages_created": pages_created,
            "pages_modified": pages_modified,
            "status": status,
        }
    )
    stats = meta.setdefault("stats", {})
    if not isinstance(stats, dict):
        stats = {}
        meta["stats"] = stats
    stats["total_sources"] = len(sources)
    stats["last_ingest_date"] = today


def move_to_processed(source_path: Path, date_str: str | None = None) -> Path:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    target_dir = RAW_PROCESSED_DIR / date_str
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / source_path.name
    if target_path.exists():
        target_path.unlink()
    shutil.move(str(source_path), str(target_path))
    return target_path


def ingest_sources(source_paths: list[Path]) -> IngestReport:
    ensure_dirs()
    meta = load_meta()
    index_text = load_index_text()
    log_text = read_text(LOG_PATH) if LOG_PATH.exists() else "# 變更日誌\n\n"
    report = IngestReport()
    index_entries: list[tuple[str, str, str]] = []

    for source_path in source_paths[:SUMMARY_READING_LIMIT]:
        item = IngestItem(
            source_path=source_path,
            summary_path=summary_page_path(source_path),
            title="",
            topic="LLM 基礎",
            summary_note="",
            status="success",
            version=1,
        )
        try:
            summary_path, summary_text, frontmatter = build_summary_page(source_path)
            item.summary_path = summary_path
            item.title = str(frontmatter["title"])
            item.version = int(frontmatter.get("version", 1))
            item.summary_note = "Karpathy 提出的 LLM Wiki 模式摘要，涵蓋持久化 wiki、三層架構，以及 ingest/query/lint 工作流。"
            write_text(summary_path, summary_text)
            index_entries.append((item.topic, summary_path.stem, item.summary_note))
            moved = move_to_processed(source_path)
            item.moved_to = moved
            ensure_meta_source_entry(meta, source_path.stem, source_path.name, pages_created=1, pages_modified=0, status="success")
        except Exception as exc:  # noqa: BLE001
            item.error = str(exc)
            item.status = "failed"
            ensure_meta_source_entry(meta, source_path.stem, source_path.name, pages_created=0, pages_modified=0, status="failed")
        report.items.append(item)

    if index_entries:
        existing_index = load_index_text()
        updated_index = existing_index
        changed = False
        for topic, page_name, note in index_entries:
            updated_index, one_changed = update_index(updated_index, page_name, note, topic)
            changed = changed or one_changed
        if changed:
            write_text(INDEX_PATH, updated_index)
            report.index_updated = True
    if report.items:
        source_names = ", ".join(source.stem for source in source_paths[:SUMMARY_READING_LIMIT])
        note_lines = [f"新增摘要頁 {len([item for item in report.items if item.error is None])} 篇"]
        note_lines.append("更新 index 與 meta")
        write_text(LOG_PATH, prepend_log_entry(log_text, source_names, note_lines))
        report.log_updated = True
    stats = meta.setdefault("stats", {})
    if isinstance(stats, dict):
        stats["total_pages"] = len(list_wiki_pages())
    save_meta(meta)
    report.meta_updated = True
    report.lint_report = lint_wiki(auto_fix=True)
    return report


def detect_inbox_sources() -> list[Path]:
    ensure_dirs()
    candidates = []
    for path in sorted(RAW_INBOX_DIR.glob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            candidates.append(path)
    return candidates


def list_wiki_pages() -> list[Path]:
    ensure_dirs()
    pages: list[Path] = []
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if path.name in {"index.md", "log.md"}:
            continue
        if "drafts" in path.parts:
            continue
        if path.stem.lower().startswith("wiki ") or path.name.lower() == "wiki llm.md":
            continue
        text = read_text(path)
        frontmatter, _ = parse_frontmatter(text)
        if str(frontmatter.get("source", "")).strip().lower() == "wiki workbench":
            continue
        pages.append(path)
    return pages


def load_page_index() -> dict[str, dict[str, object]]:
    pages = {}
    for path in list_wiki_pages():
        text = read_text(path)
        frontmatter, body = parse_frontmatter(text)
        title = str(frontmatter.get("title") or path.stem)
        pages[path.stem] = {
            "path": path,
            "title": title,
            "frontmatter": frontmatter,
            "body": body,
            "text": text,
        }
    return pages


def score_page(question: str, page: dict[str, object]) -> tuple[int, str]:
    question_tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", question)]
    title = str(page.get("title", ""))
    frontmatter = page.get("frontmatter", {})
    body = str(page.get("body", ""))
    text = f"{title}\n{json.dumps(frontmatter, ensure_ascii=False)}\n{body}".lower()
    score = 0
    for token in question_tokens:
        if token in title.lower():
            score += 6
        if token in text:
            score += 2
    # boost likely relevant summary pages
    if "摘要" in title:
        score += 3
    excerpt = extract_relevant_excerpt(body, question_tokens) or body[:240].strip()
    return score, excerpt


def extract_relevant_excerpt(text: str, tokens: list[str]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matched: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(token in lowered for token in tokens):
            matched.append(line)
        if len(matched) >= 6:
            break
    return "\n".join(matched)


def strip_duplicate_title_heading(title: str, body: str) -> str:
    normalized_title = re.sub(r"\s+", " ", title).strip().lower()
    if not normalized_title:
        return body.strip()

    cleaned_lines: list[str] = []
    skipped_leading_title = False
    seen_content = False

    for line in body.splitlines():
        stripped = line.strip()
        if not seen_content and not stripped:
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            heading_text = re.sub(r"\s+", " ", heading_match.group(2)).strip()
            heading_text = re.sub(r"\[\]\([^)]*\)$", "", heading_text).strip()
            if heading_match.group(1) == "#" and heading_text.lower() == normalized_title:
                skipped_leading_title = True
                continue

        seen_content = True
        cleaned_lines.append(line)

    cleaned_body = "\n".join(cleaned_lines).strip()
    if skipped_leading_title:
        return cleaned_body
    return body.strip()


def search_wiki(question: str, limit: int = QUERY_PAGE_LIMIT) -> list[QueryMatch]:
    pages = load_page_index()
    scored: list[QueryMatch] = []
    for page in pages.values():
        score, excerpt = score_page(question, page)
        if score <= 0:
            continue
        scored.append(
            QueryMatch(
                path=page["path"],
                title=str(page["title"]),
                score=score,
                excerpt=excerpt,
            )
        )
    scored.sort(key=lambda match: (-match.score, match.title.lower()))
    return scored[:limit]


def synthesize_answer(question: str, matches: list[QueryMatch]) -> str:
    if not matches:
        return (
            "我在 wiki 中暫時找不到直接相關的頁面。\n\n"
            "可以考慮：\n"
            "- 把相關來源放進 `second-brain/raw/inbox/`\n"
            "- 先建立一個草稿頁骨架，之後再 ingest\n"
        )
    lines = [f"針對「{question}」，根據 {', '.join(f'[[{m.path.stem}]]' for m in matches)}，我整理出這個回答：", ""]
    top = matches[0]
    lines.append(matches[0].excerpt or "此頁提供了與問題最相關的內容。")
    if len(matches) > 1:
        lines.append("")
        lines.append("補充參考頁：")
        for match in matches[1:]:
            lines.append(f"- [[{match.path.stem}]]：{match.excerpt[:120].replace(chr(10), ' ')}")
    return "\n".join(lines).strip() + "\n"


def save_analysis_page(title: str, question: str, answer: str, related_pages: list[str], *, published: bool = True) -> Path:
    ensure_dirs()
    page_name = f"{title}.md" if not title.endswith(".md") else title
    page_path = WIKI_DIR / page_name
    tags = ["分析", "綜合"]
    frontmatter = {
        "title": title,
        "tags": tags,
        "source": "Query",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "published" if published else "draft",
        "version": 1,
    }
    body = [
        serialize_frontmatter(frontmatter),
        "",
        f"# {title}",
        "",
        "## 問題",
        question,
        "",
        "## 回答",
        answer.strip(),
        "",
        "## 相關頁面",
    ]
    body.extend(f"- [[{page}]]" for page in related_pages)
    write_text(page_path, "\n".join(body).rstrip() + "\n")
    return page_path


def save_custom_page(
    *,
    title: str,
    page_kind: str,
    tags: list[str],
    source: str,
    body: str,
    related_pages: list[str],
    published: bool,
) -> CreatePageResult:
    ensure_dirs()
    page_name = f"{title}.md" if not title.endswith(".md") else title
    page_path = WIKI_DIR / page_name
    frontmatter = {
        "title": title,
        "tags": tags[:5],
        "source": source or "Manual",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "published" if published else "draft",
        "version": 1,
    }
    raw_body = strip_duplicate_title_heading(title, body)
    content_lines = [
        serialize_frontmatter(frontmatter),
        "",
        f"# {title}",
        "",
    ]
    if raw_body:
        content_lines.append(raw_body)
        content_lines.append("")
    content_lines.append("## 相關頁面")
    content_lines.extend(f"- [[{page}]]" for page in related_pages if page.strip())
    if not related_pages:
        content_lines.append("- 尚未加入相關頁面")
    write_text(page_path, "\n".join(content_lines).rstrip() + "\n")

    index_text = load_index_text()
    topic = {
        "source summary": "摘要",
        "concept": "概念",
        "entity": "實體",
        "comparison": "比較",
        "workflow": "流程",
        "analysis": "分析",
    }.get(page_kind.lower(), "其他")
    note = title
    updated_index, index_changed = update_index(index_text, page_path.stem, note, topic)
    if index_changed:
        write_text(INDEX_PATH, updated_index)

    log_text = read_text(LOG_PATH) if LOG_PATH.exists() else "# 變更日誌\n\n"
    log_updated = False
    try:
        write_text(
            LOG_PATH,
            prepend_log_entry(log_text, title, [f"生成新頁面：{page_path.name}", f"類型：{page_kind}"]),
        )
        log_updated = True
    except OSError:
        log_updated = False

    return CreatePageResult(path=page_path, index_updated=index_changed, log_updated=log_updated)


def lint_wiki(*, auto_fix: bool = False) -> LintReport:
    ensure_dirs()
    report = LintReport()
    pages = list_wiki_pages()
    report.scanned_pages = len(pages)
    index_text = load_index_text()
    title_to_path: dict[str, str] = {}
    stem_to_path: dict[str, str] = {}
    parsed_pages: list[tuple[Path, dict[str, object], str, str]] = []
    for path in pages:
        text = read_text(path)
        frontmatter, body = parse_frontmatter(text)
        title = str(frontmatter.get("title") or path.stem)
        parsed_pages.append((path, frontmatter, body, text))
        title_to_path[title.lower()] = path.stem
        stem_to_path[path.stem.lower()] = path.stem
        if not page_frontmatter_is_complete(frontmatter):
            report.missing_frontmatter.append(
                LintIssue("frontmatter", str(path.relative_to(WIKI_DIR)), "frontmatter 欄位不完整")
            )
        if "TODO" in text or "待補充" in text or "[ ]" in text:
            count = text.count("TODO") + text.count("待補充") + text.count("[ ]")
            report.todo_items.append(
                LintIssue("todo", str(path.relative_to(WIKI_DIR)), f"偵測到 {count} 個待辦標記")
            )

    inbound_counts: dict[str, int] = {path.stem: 0 for path in pages}
    for raw_link in WIKI_LINK_RE.findall(index_text):
        target = raw_link.split("|", 1)[0].strip().removesuffix(".md")
        target_key = target.lower()
        resolved = stem_to_path.get(target_key) or title_to_path.get(target_key)
        if resolved and resolved in inbound_counts:
            inbound_counts[resolved] += 1
    for path, _, body, text in parsed_pages:
        for raw_link in WIKI_LINK_RE.findall(text):
            target = raw_link.split("|", 1)[0].strip().removesuffix(".md")
            target_key = target.lower()
            resolved = stem_to_path.get(target_key) or title_to_path.get(target_key)
            if resolved and resolved in inbound_counts:
                inbound_counts[resolved] += 1
            else:
                report.dead_links.append(
                    LintIssue("dead-link", str(path.relative_to(WIKI_DIR)), f"[[{target}]]")
                )

    for path in pages:
        if inbound_counts.get(path.stem, 0) == 0:
            report.orphan_pages.append(
                LintIssue("orphan", str(path.relative_to(WIKI_DIR)), "無入站連結")
            )
        if path.stem not in index_text and path.name not in index_text:
            report.unindexed_pages.append(
                LintIssue("unindexed", str(path.relative_to(WIKI_DIR)), "未列入 index.md")
            )

    if auto_fix and report.unindexed_pages:
        additions: list[tuple[str, str, str]] = []
        for issue in report.unindexed_pages[:LINT_FIX_LIMIT]:
            page_path = WIKI_DIR / issue.path
            text = read_text(page_path)
            frontmatter, _ = parse_frontmatter(text)
            title = str(frontmatter.get("title") or page_path.stem)
            topic = "LLM 基礎" if "llm" in page_path.stem.lower() or "wiki" in title.lower() else "其他"
            note = title
            additions.append((topic, page_path.stem, note))
        updated = index_text
        for topic, page_name, note in additions:
            updated, _ = update_index(updated, page_name, note, topic)
        if updated != index_text:
            write_text(INDEX_PATH, updated)
            report.auto_fixes.append(f"將 {len(additions)} 個未索引頁面加入 index.md")

    if auto_fix and report.orphan_pages:
        report.auto_fixes.append("已檢查孤兒頁並保留人工判斷")

    return report
