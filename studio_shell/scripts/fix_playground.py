import sys
from pathlib import Path

# 取得專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parents[2]
target_file = PROJECT_ROOT / "studio_shell" / "pages" / "2_Playground.py"

new_content = """from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studioint_shell.shell_ui import inject_style # 修正可能的 import 錯誤，但先維持原樣或根據實際情況

# 為了確保安全，我們直接用原本的內容結構，只修改 return 部分
"""

# 由於我不能直接用 edit_file 處理複雜的邏輯，我決定直接寫入一個完整的、正確的版本
# 我會先讀取原本的內容，然後在最後面做邏輯替換

with open(target_file, 'r', encoding='utf-8') as f:
    original_code = f.read()

# 尋找 return "" 的位置並替換
# 我們要建立一個 summary 字串
replacement_logic = """
    # 1. 整理資料
    summary_data = {
        "暱稱": nickname or "（未填）",
        "心情": mood,
        "能量": f"{energy}/10",
        "今日事件": event or "（未填）",
        "計數器": st.session_state.playground_count,
    }
    
    # 2. 格式化成 Extra Context 字串
    extra_context = "\\n".join([f"- {k}: {v}" for k, v in summary_data.items()])
    extra_context_header = "### [Extra Context]\\n"
    full_context = extra_context_header + extra_context

    # 3. 在畫面上顯示「給 Agent 的摘要」
    st.markdown("#### 給 Agent 的摘要")
    st.code(full_context, language="text")

    # 4. 最後 return 這段摘要
    return full_context
"""

# 尋找原本的 return "" 並替換
import re
# 尋找最後的 return "" 及其前後的邏輯
new_code = re.sub(r'return\s*""', replacement_logic, original_code)

with open(target_file, 'arg', 'w', encoding='utf-8') as f:
    f.write(new_code)

print("Successfully updated 2_Playground.py")
