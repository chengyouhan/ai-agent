from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


def st_copy_to_clipboard(text: str, *, key: str) -> None:
    """Render a small copy-to-clipboard button using a temporary streamlit component."""
    import html
    import uuid

    component_key = f"{key}_{uuid.uuid4().hex[:8]}"
    safe_text = html.escape(text).replace("\\", "\\\\").replace("\n", "\\n")
    st.markdown(
        f"""
        <script>
        function copyText_{component_key}() {{
            navigator.clipboard.writeText(`{safe_text}`).then(() => {{
                const btn = document.getElementById('btn_{component_key}');
                if (btn) {{ btn.innerText = '✓ 已複製'; setTimeout(() => btn.innerText = '📋 複製', 1500); }}
            }});
        }}
        </script>
        <button id="btn_{component_key}" onclick="copyText_{component_key}()" style="
            width:100%; padding:0.35rem 0.6rem; border-radius:6px; border:1px solid rgba(250,250,250,0.2);
            background:rgba(255,255,255,0.08); cursor:pointer; color:inherit;
        ">📋 複製</button>
        """,
        unsafe_allow_html=True,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHELL_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import studio_shell.agent_panel as agent_panel
from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import format_extra_context, inject_style, load_page_data, save_page_data, shared_data_path
import studio_shell.wiki_skill as wiki_skill
from importlib import reload as _reload_wiki_skill
from importlib import reload as _reload_agent_panel

_reload_agent_panel(agent_panel)

# 避免 Streamlit MPA 在多頁面 import 時載入到過時的位元碼快取
_reload_wiki_skill(wiki_skill)

PAGE_NAME = "Wiki Workbench"

st.set_page_config(page_title="Wiki 工作台", page_icon="W", layout="wide")
inject_style()

MODES = ["Ingest", "Query", "Create", "Lint"]


def _render_inbox_panel() -> None:
    sources = wiki_skill.detect_inbox_sources()
    st.caption(f"raw/inbox：{wiki_skill.RAW_INBOX_DIR}")
    if not sources:
        st.info("raw/inbox 目前沒有可 ingest 的新來源。")
        return
    st.write(f"找到 {len(sources)} 個候選來源。")
    for path in sources[:10]:
        st.code(str(path), language="text")
    if len(sources) > 10:
        st.caption("一次最多顯示 10 個候選；ingest 也會以 10 個為上限。")


def _render_ingest() -> str:
    st.markdown("#### Ingest")
    _render_inbox_panel()
    auto_lint = st.checkbox("Ingest 後自動執行 lint", value=True)
    report_text = ""
    if st.button("執行 ingest", type="primary", use_container_width=True):
        sources = wiki_skill.detect_inbox_sources()
        if not sources:
            st.warning("raw/inbox 沒有新來源。")
        else:
            report = wiki_skill.ingest_sources(sources)
            lines = [
                f"已處理 {report.processed_count}/{report.total_count} 個來源。",
                f"index 更新：{report.index_updated}",
                f"log 更新：{report.log_updated}",
                f"meta.json 更新：{report.meta_updated}",
            ]
            st.success("Ingest 完成")
            for item in report.items:
                if item.error:
                    st.error(f"{item.source_path.name}：{item.error}")
                else:
                    st.write(f"✓ {item.source_path.name} -> {item.summary_path.name}")
                    if item.moved_to:
                        st.caption(f"已移至 {item.moved_to}")
            if report.lint_report and auto_lint:
                st.markdown("##### Lint 結果")
                st.markdown(report.lint_report.to_markdown())
            report_text = "\n".join(lines)
    return report_text or "等待 ingest。"


def _render_query() -> str:
    st.markdown("#### Query")
    question = st.text_area(
        "問題 / query",
        value=st.session_state.get("wiki_query_question", "LLM Wiki 的核心理念是什麼？"),
        placeholder="輸入你想查的 wiki 問題",
        height=90,
    )
    st.session_state["wiki_query_question"] = question
    analysis_title = st.text_input(
        "分析頁標題",
        value=st.session_state.get("wiki_query_title", "Query-分析"),
    )
    st.session_state["wiki_query_title"] = analysis_title
    saved_path = None
    answer = ""
    matches = []
    if st.button("搜尋 wiki", use_container_width=True):
        matches = wiki_skill.search_wiki(question, limit=wiki_skill.QUERY_PAGE_LIMIT)
        st.session_state["wiki_query_matches"] = [match.path.stem for match in matches]
        st.session_state["wiki_query_answer"] = wiki_skill.synthesize_answer(question, matches)
        if not matches:
            st.warning("wiki 中暫時找不到相關頁面。")
            answer = st.session_state["wiki_query_answer"]
        else:
            st.success(f"找到 {len(matches)} 個相關頁面")
            for match in matches:
                st.write(f"[[{match.path.stem}]] — score {match.score}")
                st.code(match.excerpt or "(no excerpt)", language="text")
            answer = st.session_state["wiki_query_answer"]
            st.markdown("##### 綜合回答")
            st.write(answer)
    if st.session_state.get("wiki_query_answer"):
        answer = st.session_state["wiki_query_answer"]
        st.markdown("##### 綜合回答")
        st.write(answer)
    if st.button("保存分析為新頁面", use_container_width=True, disabled=not bool(st.session_state.get("wiki_query_answer", "").strip())):
        related = st.session_state.get("wiki_query_matches", [])
        saved_path = wiki_skill.save_analysis_page(
            title=analysis_title,
            question=question,
            answer=st.session_state.get("wiki_query_answer", ""),
            related_pages=list(related) if isinstance(related, list) else [],
            published=True,
        )
        st.success(f"已保存：{saved_path}")
    return answer or st.session_state.get("wiki_query_answer", "") or "等待查詢。"


_PAGE_KIND_LABELS: dict[str, str] = {
    "Concept": "概念",
    "Entity": "實體",
    "Comparison": "比較",
    "Workflow": "流程",
    "Analysis": "分析",
    "Source Summary": "來源摘要",
}


def _build_agent_prompt(title: str, page_kind: str, source: str, related_pages: list[str], topic: str) -> str:
    kind_label = _PAGE_KIND_LABELS.get(page_kind, page_kind)
    related_section = "\n".join(f"- [[{page}]]" for page in related_pages if page.strip()) or "- 尚未指定"
    return (
        f"請幫我為 LLM Wiki 建立一篇「{kind_label}」頁面。\n\n"
        f"【頁面標題】{title}\n"
        f"【頁面類型】{kind_label}\n"
        f"【來源/背景】{source or 'Manual'}\n"
        f"【query / 想整理的主題或問題】\n{topic}\n\n"
        f"【相關頁面】\n{related_section}\n\n"
        "請參考 skills/llm-wiki/references/schema.md 的頁面模板，生成完整的 Markdown 正文（不含 frontmatter）。\n"
        f"不要輸出頁面主標題，也不要重複寫 `# {title}`；正文請直接從前言段落或 `##` 次標題開始。\n"
        "請明確回應上面的 query / 問題，不要只寫泛泛介紹。\n"
        "回覆時請把建議正文放在以下區塊中：\n\n"
        "【建議內容】\n"
        "（這裡放你生成的 Markdown 內容，包含適當的標題、段落、列表或表格）\n"
        "【建議內容結束】\n\n"
        "如果資訊不足，請在區塊外先說明還需要什麼資訊，但仍盡量給出一版草稿。"
    )


def _extract_suggested_body(agent_reply: str) -> str:
    text = (agent_reply or "").strip()
    start_marker = "【建議內容】"
    end_marker = "【建議內容結束】"
    if start_marker in text and end_marker in text:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker, start)
        body = text[start:end].strip()
        if body:
            return body
    return text


def _render_create() -> str:
    st.markdown("#### Create")
    title = st.text_input(
        "頁面標題",
        value=st.session_state.get("wiki_create_title", "New Wiki Page"),
        placeholder="例如：LLM 架構、提示詞設計、工作流程",
    )
    st.session_state["wiki_create_title"] = title
    page_kind = st.selectbox(
        "頁面類型",
        ["Concept", "Entity", "Comparison", "Workflow", "Analysis", "Source Summary"],
        index=st.session_state.get("wiki_create_kind_index", 0),
    )
    st.session_state["wiki_create_kind_index"] = ["Concept", "Entity", "Comparison", "Workflow", "Analysis", "Source Summary"].index(page_kind)
    tags_text = st.text_input(
        "標籤",
        value=st.session_state.get("wiki_create_tags", "wiki, draft"),
        help="用逗號分隔，最多 5 個。",
    )
    st.session_state["wiki_create_tags"] = tags_text
    related_text = st.text_input(
        "相關頁面",
        value=st.session_state.get("wiki_create_related", ""),
        placeholder="用逗號分隔，例如：raw/inbox/llm-wiki-karpathy.md, LLM-Wiki-Karpathy-摘要.md, index.md",
    )
    st.session_state["wiki_create_related"] = related_text
    related_pages = [item.strip() for item in related_text.split(",") if item.strip()]

    # 若相關頁面中有 raw/inbox 或 raw/processed 路徑，自動推斷為主要來源
    inferred_source = "Manual"
    for page in related_pages:
        lowered = page.lower()
        if lowered.startswith("raw/inbox/") or lowered.startswith("raw/processed/") or lowered.startswith("http"):
            inferred_source = page
            break

    previous_inferred_source = st.session_state.get("wiki_create_inferred_source", "Manual")
    current_source = st.session_state.get("wiki_create_source")
    if current_source in (None, "", "Manual") or current_source == previous_inferred_source:
        st.session_state["wiki_create_source"] = inferred_source
    st.session_state["wiki_create_inferred_source"] = inferred_source

    source = st.text_input(
        "主要來源（可選，會自動從相關頁面推斷）",
        key="wiki_create_source",
        placeholder="預設為 Manual；若有 raw/... 或 http 會自動帶入",
        help="可手動覆寫，或留空讓系統根據「相關頁面」自動判斷。",
    )
    topic = st.text_area(
        "想整理的主題 / 請 Agent 協助的問題",
        value=st.session_state.get("wiki_create_topic", ""),
        placeholder="描述你想讓 Agent 整理的主題、概念或問題。例如：什麼是 LLM Wiki？它跟傳統 Markdown Wiki 差在哪？",
        height=120,
    )
    st.session_state["wiki_create_topic"] = topic

    agent_prompt = _build_agent_prompt(
        title.strip() or "New Wiki Page",
        page_kind,
        source.strip() or inferred_source,
        related_pages,
        topic.strip(),
    )

    col_prompt, col_copy = st.columns([6, 1])
    with col_prompt:
        st.markdown("##### 給 Agent 的提示詞")
    with col_copy:
        st_copy_to_clipboard(agent_prompt, key="wiki_create_copy_prompt")
    st.code(agent_prompt, language="text")
    st.caption("可手動複製到右欄，或直接按下方「請 Agent 產生草稿」自動送出。")

    agent_ok, agent_message = agent_panel.can_run_agent_for_current_session()
    draft_col, info_col = st.columns([1.2, 2.8])
    with draft_col:
        auto_draft = st.button(
            "請 Agent 產生草稿",
            use_container_width=True,
            disabled=not agent_ok,
        )
    with info_col:
        if agent_ok:
            st.caption("會使用右欄目前的對話與 Agent session，自動產生草稿並填入下方正文欄位。")
        else:
            st.caption(agent_message or "請先準備右欄 Agent。")

    if auto_draft:
        with st.spinner("Agent 正在整理草稿..."):
            try:
                reply, _reasoning = agent_panel.run_agent_prompt_for_current_session(
                    agent_prompt,
                    display_user_text=f"[Wiki Create 草稿] {title.strip() or 'New Wiki Page'}",
                )
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                suggested_body = _extract_suggested_body(reply)
                st.session_state["wiki_create_body"] = suggested_body
                st.success("已自動產生草稿，並填入下方「Agent 回覆內容」。")
                st.rerun()

    body = st.text_area(
        "Agent 回覆內容（貼上後生成頁面）",
        value=st.session_state.get("wiki_create_body", ""),
        placeholder="把右欄 Agent 回覆中【建議內容】...【建議內容結束】之間的 Markdown 貼到這裡。",
        height=220,
    )
    st.session_state["wiki_create_body"] = body
    published = st.checkbox("直接發布", value=st.session_state.get("wiki_create_published", True))
    st.session_state["wiki_create_published"] = published

    saved_path = None
    if st.button("生成新頁面", type="primary", use_container_width=True):
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
        result = wiki_skill.save_custom_page(
            title=title.strip() or "New Wiki Page",
            page_kind=page_kind,
            tags=tags,
            source=source.strip() or "Manual",
            body=body,
            related_pages=related_pages,
            published=published,
        )
        saved_path = result.path
        st.success(f"已生成：{saved_path}")
        if result.index_updated:
            st.caption("index.md 已更新")
        if result.log_updated:
            st.caption("log.md 已更新")
    return str(saved_path) if saved_path else "等待建立新頁面。"


def _render_lint() -> str:
    st.markdown("#### Lint")
    auto_fix = st.checkbox("自動修復未索引頁面", value=True)
    report_text = ""
    if st.button("執行 lint", use_container_width=True):
        report = wiki_skill.lint_wiki(auto_fix=auto_fix)
        report_text = report.to_markdown()
        st.markdown(report_text)
        if report.auto_fixes:
            st.success("Lint 完成，已執行部分自動修復。")
        else:
            st.info("Lint 完成。")
    return report_text or "等待 lint。"


def render_main() -> str:
    state = load_page_data(PAGE_NAME, shell_root=SHELL_ROOT)
    mode = st.radio("模式", MODES, horizontal=True, index=int(state.get("mode_index", 0)) if str(state.get("mode_index", "0")).isdigit() else 0)

    save_page_data(PAGE_NAME, {"mode_index": MODES.index(mode)}, shell_root=SHELL_ROOT)

    context = ""
    if mode == "Ingest":
        context = _render_ingest()
    elif mode == "Query":
        context = _render_query()
    elif mode == "Create":
        context = _render_create()
    else:
        context = _render_lint()

    st.divider()
    st.markdown("#### Current Context")
    st.code(
        format_extra_context(
            PAGE_NAME,
            mode=mode,
            inbox=str(wiki_skill.RAW_INBOX_DIR),
            wiki=str(wiki_skill.WIKI_DIR),
            note=context or "等待操作",
        ),
        language="text",
    )
    return context


page_shell(
    "Wiki 工作台",
    "依 `llm-wiki` skill 操作 raw/inbox、wiki、index、log 與 lint。",
    render_main,
    page_name=PAGE_NAME,
)
