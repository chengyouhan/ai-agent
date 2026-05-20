import base64
import copy
import json
import mimetypes
import os
import platform
import shlex
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    message_chunk_to_message,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai import AuthenticationError


PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_DIR = PROJECT_ROOT / "memory"
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"
HISTORY_FILE = MEMORY_DIR / "HISTORY.md"
TRANSCRIPT_FILE = MEMORY_DIR / "transcript.jsonl"
SESSION_ID = str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_relative_path(path_text: str) -> Path:
    candidate = (PROJECT_ROOT / path_text).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"path escapes workspace: {path_text}") from exc
    return candidate


def ensure_memory_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def get_identity() -> str:
    return f"""You are a practical coding agent running inside this workspace.

Identity and environment:
- OS: {platform.system()} {platform.release()}
- Python: {sys.version.split()[0]}
- Workspace: {PROJECT_ROOT}

Operating rules:
- Help the user complete real tasks, especially coding tasks.
- Prefer reading files before editing them.
- You may use tools to read files, write files, list directories, and run shell commands.
- Keep shell work scoped to the workspace unless the user clearly asks otherwise.
- When a skill is relevant, read its SKILL.md first and follow its instructions.
- Do not expose secrets, API keys, or private environment values."""


@dataclass
class SkillEntry:
    name: str
    path: Path
    source: str
    description: str
    always: bool
    body: str


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, text

    meta: dict[str, str] = {}
    for raw in lines[1:end]:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")

    body = "\n".join(lines[end + 1 :]).strip()
    return meta, body


class SkillsLoader:
    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None) -> None:
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or (
            Path.home() / ".codex" / "skills" / ".system"
        )

    def _entries_from_dir(
        self, root: Path, source: str, skip: set[str]
    ) -> list[SkillEntry]:
        if not root.exists():
            return []

        entries: list[SkillEntry] = []
        for skill_dir in sorted(root.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.exists():
                continue
            if skill_dir.name in skip:
                continue

            text = skill_file.read_text(encoding="utf-8")
            meta, body = split_frontmatter(text)
            name = skill_dir.name
            description = meta.get("description") or name
            always = meta.get("always", "false").lower() == "true"
            entries.append(SkillEntry(name, skill_file, source, description, always, body))
        return entries

    def list_skills(self) -> list[SkillEntry]:
        workspace_entries = self._entries_from_dir(self.workspace_skills, "workspace", set())
        workspace_names = {entry.name for entry in workspace_entries}
        builtin_entries = self._entries_from_dir(
            self.builtin_skills, "builtin", workspace_names
        )
        return workspace_entries + builtin_entries

    def load_skill(self, name: str) -> str | None:
        for root in (self.workspace_skills, self.builtin_skills):
            path = root / name / "SKILL.md"
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None


def build_skills_summary(entries: list[SkillEntry]) -> str:
    summarized = [entry for entry in entries if not entry.always]
    if not summarized:
        return ""
    lines = [
        f"- **{entry.name}**: {entry.description} (`{entry.path}`)"
        for entry in summarized
    ]
    return "\n".join(lines)


def memory_block_for_system() -> str:
    if not MEMORY_FILE.exists():
        return ""
    text = MEMORY_FILE.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    return f"# Long-term Memory\n\n{text}"


def build_system_prompt(loader: SkillsLoader) -> str:
    parts: list[str] = [get_identity()]
    mem = memory_block_for_system()
    if mem:
        parts.append(mem)

    entries = loader.list_skills()
    active = [entry for entry in entries if entry.always]
    if active:
        body = "\n\n---\n\n".join(
            f"### Skill: {entry.name}\n\n{entry.body}" for entry in active
        )
        parts.append(f"# Active Skills\n\n{body}")

    summary = build_skills_summary(entries)
    if summary:
        intro = (
            "Available skills are listed below. If a skill is relevant, use read_file "
            "to inspect the matching SKILL.md before applying it."
        )
        parts.append(f"# Skills\n\n{intro}\n\n{summary}")
    return "\n\n---\n\n".join(parts)


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file from the workspace."""
    full = safe_relative_path(path)
    return full.read_text(encoding="utf-8")


@tool
def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a workspace file, creating parent folders if needed."""
    full = safe_relative_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return f"wrote {full.relative_to(PROJECT_ROOT)}"


@tool
def replace_in_file(path: str, old: str, new: str, count: int = 1) -> str:
    """Replace text inside a workspace file."""
    full = safe_relative_path(path)
    text = full.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError("old text not found")
    updated = text.replace(old, new, count)
    full.write_text(updated, encoding="utf-8")
    changed = text.count(old) if count < 0 else min(text.count(old), count)
    return f"replaced {changed} occurrence(s) in {full.relative_to(PROJECT_ROOT)}"


@tool
def list_dir(path: str = ".") -> str:
    """List files and directories under a workspace path."""
    full = safe_relative_path(path)
    if not full.is_dir():
        raise ValueError(f"not a directory: {path}")
    rows = []
    for item in sorted(full.iterdir()):
        marker = "/" if item.is_dir() else ""
        rows.append(f"{item.name}{marker}")
    return "\n".join(rows)


@tool
def exec_shell(command: str) -> str:
    """Run a shell command in the workspace and return stdout and stderr."""
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        shell=True,
        text=True,
        capture_output=True,
        timeout=60,
    )
    output = completed.stdout
    if completed.stderr:
        output += ("\n" if output else "") + completed.stderr
    if not output:
        output = f"(exit code {completed.returncode}, no output)"
    else:
        output += f"\n(exit code {completed.returncode})"
    return output[-12000:]


TOOLS = [read_file, write_file, replace_in_file, list_dir, exec_shell]


def estimate_message_tokens(message: BaseMessage | str) -> int:
    if isinstance(message, BaseMessage):
        text = str(message.content)
        if isinstance(message, AIMessage) and message.tool_calls:
            text += json.dumps(message.tool_calls, ensure_ascii=False)
    else:
        text = message
    return max(1, len(text))


def estimate_messages_tokens(messages: list[BaseMessage]) -> int:
    return sum(estimate_message_tokens(message) for message in messages)


def token_budget() -> int:
    return int(os.getenv("TOKEN_BUDGET", "12000"))


def tool_output_char_limit() -> int:
    return int(os.getenv("TOOL_OUTPUT_CHAR_LIMIT", "4000"))


def pick_consolidation_boundary(history: list[BaseMessage], budget: int) -> int:
    if estimate_messages_tokens(history) <= budget:
        return 0

    running = 0
    boundary = 0
    target = max(1, budget // 2)
    for index, message in enumerate(reversed(history), start=1):
        running += estimate_message_tokens(message)
        if running >= target:
            boundary = len(history) - index
            break

    while boundary < len(history) and isinstance(history[boundary], ToolMessage):
        boundary += 1
    return max(0, boundary)


def message_to_plain_text(message: BaseMessage) -> str:
    role = message.type
    content = message.content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, dict) and block.get("type") == "image_url":
                parts.append("[image]")
        content = "\n".join(parts)
    return f"{role}: {content}"


def consolidate_memory(llm: ChatOpenAI, history: list[BaseMessage]) -> list[BaseMessage]:
    boundary = pick_consolidation_boundary(history, token_budget())
    if boundary <= 0:
        return history

    ensure_memory_dir()
    past = history[:boundary]
    recent = history[boundary:]
    existing = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
    transcript = "\n".join(message_to_plain_text(message) for message in past)
    prompt = (
        "Update the long-term memory for this agent. Keep durable user preferences, "
        "project facts, decisions, and unresolved tasks. Drop transient chatter.\n\n"
        f"Existing memory:\n{existing or '(empty)'}\n\n"
        f"New transcript to consolidate:\n{transcript}"
    )
    response = llm.invoke(
        [
            SystemMessage(content="You maintain concise long-term project memory."),
            HumanMessage(content=prompt),
        ]
    )
    MEMORY_FILE.write_text(str(response.content).strip() + "\n", encoding="utf-8")
    with HISTORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"\n\n## Consolidated {now_iso()}\n\n{transcript}\n")
    return recent


def image_bytes_to_data_url(data: bytes, media_type: str) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{media_type};base64,{b64}"


def guess_media_type(path: Path, fallback: str = "image/png") -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed and guessed.startswith("image/"):
        return guessed
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return fallback


def user_row_dict(
    text: str, image_rel: str | None, media_type: str | None = None
) -> dict[str, Any]:
    row: dict[str, Any] = {"role": "user", "content": text}
    if image_rel:
        row["image_path"] = image_rel
        if media_type:
            row["media_type"] = media_type
    return row


def load_user_row_to_history_human(row: dict[str, Any]) -> HumanMessage:
    text = str(row.get("content", ""))
    rel = row.get("image_path")
    if not rel:
        return HumanMessage(content=text)
    media_type = row.get("media_type")
    extra = f"[Image was attached from workspace path: {rel}]"
    if media_type:
        extra += f" (media_type={media_type})"
    return HumanMessage(content=f"{text}\n\n{extra}")


def build_human_message_for_current_turn(
    text: str, image_rel: Path | None, project_root: Path
) -> HumanMessage:
    if image_rel is None:
        return HumanMessage(content=text)

    full = (project_root / image_rel).resolve()
    if not full.is_file():
        print(f"[warn] missing image for current turn: {image_rel}")
        return HumanMessage(content=text)

    media_type = guess_media_type(full)
    url = image_bytes_to_data_url(full.read_bytes(), media_type)
    return HumanMessage(
        content=[
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": url}},
        ]
    )


def _human_to_text_only_placeholder(message: HumanMessage) -> HumanMessage:
    content = message.content
    if isinstance(content, str):
        return message
    if isinstance(content, list):
        parts: list[str] = []
        had_image = False
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, dict) and block.get("type") == "image_url":
                had_image = True
        body = "\n".join(part for part in parts if part).strip()
        if had_image:
            body = f"{body}\n\n[Previous image omitted from history.]".strip()
        return HumanMessage(content=body or "[Previous image omitted from history.]")
    return HumanMessage(content=str(content))


def _trim_tool_message_for_model(message: ToolMessage) -> ToolMessage:
    content = str(message.content)
    limit = tool_output_char_limit()
    if len(content) <= limit:
        return message
    trimmed = content[:limit] + "\n\n[tool output truncated for model context]"
    return ToolMessage(
        content=trimmed,
        tool_call_id=message.tool_call_id,
        name=getattr(message, "name", None),
    )


def messages_for_model(
    system_message: BaseMessage,
    history: list[BaseMessage],
    human_message: HumanMessage,
) -> list[BaseMessage]:
    out: list[BaseMessage] = [copy.deepcopy(system_message)]
    for message in history:
        copied = copy.deepcopy(message)
        if isinstance(copied, HumanMessage) and not isinstance(copied.content, str):
            copied = _human_to_text_only_placeholder(copied)
        if isinstance(copied, ToolMessage):
            copied = _trim_tool_message_for_model(copied)
        out.append(copied)
    out.append(copy.deepcopy(human_message))
    return out


def append_jsonl(row: dict[str, Any]) -> None:
    ensure_memory_dir()
    row.setdefault("timestamp", now_iso())
    row.setdefault("metadata", {})
    row["metadata"].setdefault("session_id", SESSION_ID)
    with TRANSCRIPT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def serialize_message(message: BaseMessage) -> dict[str, Any]:
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    if isinstance(message, AIMessage):
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls,
        }
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
            "name": getattr(message, "name", None),
        }
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    return {"role": message.type, "content": message.content}


def row_to_message(row: dict[str, Any]) -> BaseMessage | None:
    role = row.get("role")
    if role == "user":
        return load_user_row_to_history_human(row)
    if role == "assistant":
        return AIMessage(
            content=row.get("content", ""),
            tool_calls=row.get("tool_calls") or [],
        )
    if role == "tool":
        return ToolMessage(
            content=row.get("content", ""),
            tool_call_id=row.get("tool_call_id", ""),
            name=row.get("name"),
        )
    return None


def load_history() -> list[BaseMessage]:
    if not TRANSCRIPT_FILE.exists():
        return []
    messages: list[BaseMessage] = []
    with TRANSCRIPT_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = row_to_message(row)
            if message is not None:
                messages.append(message)
    return messages


def parse_user_input(raw: str) -> tuple[str, Path | None, str | None]:
    if not raw.startswith("/image "):
        return raw, None, None

    rest = raw[len("/image ") :].strip()
    if not rest:
        return "", None, None

    try:
        parts = shlex.split(rest, posix=False)
    except ValueError:
        parts = rest.split(maxsplit=1)

    if not parts:
        return "", None, None

    image_text = parts[0].strip('"')
    text = " ".join(parts[1:]).strip() or "Please describe this image."
    full = safe_relative_path(image_text)
    rel = full.relative_to(PROJECT_ROOT)
    media_type = guess_media_type(full)
    return text, rel, media_type


def run_react_turn(
    llm: ChatOpenAI,
    system_message: SystemMessage,
    history: list[BaseMessage],
    human_message: HumanMessage,
) -> tuple[str, list[BaseMessage]]:
    model_with_tools = llm.bind_tools(TOOLS)
    turn_messages = messages_for_model(system_message, history, human_message)
    new_messages: list[BaseMessage] = [human_message]
    final_text = ""

    while True:
        ai_chunk = None
        streamed_parts: list[str] = []
        for chunk in model_with_tools.stream(turn_messages):
            ai_chunk = chunk if ai_chunk is None else ai_chunk + chunk
            text = str(chunk.content or "")
            if text:
                print(text, end="", flush=True)
                streamed_parts.append(text)

        if ai_chunk is None:
            ai_message = AIMessage(content="")
        else:
            ai_message = message_chunk_to_message(ai_chunk)

        new_messages.append(ai_message)
        append_jsonl(serialize_message(ai_message))

        if not ai_message.tool_calls:
            final_text = "".join(streamed_parts) or str(ai_message.content)
            print()
            break

        turn_messages.append(ai_message)
        for call in ai_message.tool_calls:
            tool_name = call["name"]
            selected = {item.name: item for item in TOOLS}.get(tool_name)
            if selected is None:
                content = f"unknown tool: {tool_name}"
            else:
                try:
                    content = selected.invoke(call.get("args", {}))
                except Exception as exc:
                    content = f"tool error: {type(exc).__name__}: {exc}"
            tool_message = ToolMessage(
                content=str(content),
                tool_call_id=call["id"],
                name=tool_name,
            )
            new_messages.append(tool_message)
            append_jsonl(serialize_message(tool_message))
            turn_messages.append(tool_message)

    return final_text, new_messages


def stream_plain_turn(
    llm: ChatOpenAI,
    system_message: SystemMessage,
    history: list[BaseMessage],
    human_message: HumanMessage,
) -> tuple[str, list[BaseMessage]]:
    chunks: list[str] = []
    for chunk in llm.stream(messages_for_model(system_message, history, human_message)):
        text = str(chunk.content or "")
        if text:
            print(text, end="", flush=True)
            chunks.append(text)
    print()
    content = "".join(chunks)
    ai_message = AIMessage(content=content)
    append_jsonl(serialize_message(ai_message))
    return content, [human_message, ai_message]


def create_llm() -> ChatOpenAI:
    model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL", "gpt-4o")
    kwargs: dict[str, Any] = {"model": model}

    temperature = os.getenv("TEMPERATURE")
    if temperature:
        kwargs["temperature"] = float(temperature)

    base_url = os.getenv("BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)


def looks_like_placeholder_api_key(api_key: str) -> bool:
    lowered = api_key.strip().lower()
    placeholders = ("sk-12345678", "your-api-key", "your_openai_api_key")
    return any(item in lowered for item in placeholders)


def print_auth_help() -> None:
    print(
        "OpenAI API key authentication failed. Update OPENAI_API_KEY in .env "
        "with a valid key. Placeholder values such as sk-12345678 will not work."
    )


def main() -> None:
    load_dotenv()

    agent_name = "Workshop Agent"
    message = f"Hello, 我是 {agent_name}，準備好開始協作。"
    print(message)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("找不到 OPENAI_API_KEY，請先在 .env 設定後再執行。")
        return

    loader = SkillsLoader(PROJECT_ROOT)
    llm = create_llm()
    try:
        history = consolidate_memory(llm, load_history())
    except AuthenticationError:
        print_auth_help()
        return
    print(
        "輸入訊息開始對話；輸入 /stream <prompt> 使用串流；"
        "輸入 /image <path> <prompt> 可附圖；輸入 /quit 離開。"
    )

    while True:
        try:
            raw = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue
        if raw in {"/quit", "quit", "exit"}:
            break

        try:
            text, image_rel, media_type = parse_user_input(raw)
        except Exception as exc:
            print(f"[input error] {exc}")
            continue

        stream_only = False
        if text.startswith("/stream "):
            text = text[len("/stream ") :].strip()
            stream_only = True

        system_message = SystemMessage(content=build_system_prompt(loader))
        human_message = build_human_message_for_current_turn(text, image_rel, PROJECT_ROOT)
        append_jsonl(
            user_row_dict(
                text,
                str(image_rel).replace("\\", "/") if image_rel else None,
                media_type,
            )
        )

        print("助理> ", end="", flush=True)
        try:
            if image_rel or stream_only:
                answer, new_messages = stream_plain_turn(
                    llm, system_message, history, human_message
                )
                history.extend(new_messages)
            else:
                answer, new_messages = run_react_turn(
                    llm, system_message, history, human_message
                )
                history.extend(new_messages)

            history = consolidate_memory(llm, history)
        except AuthenticationError:
            print()
            print_auth_help()
            break


if __name__ == "__main__":
    main()
