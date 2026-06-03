from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import format_extra_context, inject_style

st.set_page_config(page_title="點餐 App", page_icon="🍱", layout="wide")
inject_style()

MENU = {
    "牛肉麵": 140,
    "雞腿飯": 120,
    "滷肉飯": 65,
    "水餃": 90,
}
DRINKS = {
    "不需要": 0,
    "紅茶": 30,
    "奶茶": 40,
    "豆漿": 25,
}
ADDONS = {
    "滷蛋": 20,
    "青菜": 35,
    "湯品": 45,
}


def _format_money(amount: int) -> str:
    return f"${amount}"


def render_main() -> str:
    st.markdown("#### 建立訂單")
    if "order_submitted" not in st.session_state:
        st.session_state.order_submitted = False

    col1, col2 = st.columns(2)
    with col1:
        customer = st.text_input("訂購人", key="order_customer", placeholder="例如：小明")
        main_item = st.selectbox("主餐", list(MENU), key="order_main")
        quantity = st.number_input("數量", min_value=1, max_value=10, value=1, key="order_quantity")
    with col2:
        dining_type = st.radio("取餐方式", ["內用", "外帶"], horizontal=True, key="order_dining")
        drink = st.selectbox("飲料", list(DRINKS), key="order_drink")
        addons = st.multiselect("加點", list(ADDONS), key="order_addons")

    note = st.text_area(
        "備註",
        key="order_note",
        placeholder="例如：不要香菜、飯少一點、飲料少冰",
        height=80,
    )

    item_total = MENU[main_item] * int(quantity)
    drink_total = DRINKS[drink]
    addon_total = sum(ADDONS[name] for name in addons)
    total = item_total + drink_total + addon_total

    st.divider()
    st.markdown("#### 訂單預覽")
    m1, m2, m3 = st.columns(3)
    m1.metric("主餐小計", _format_money(item_total))
    m2.metric("加點與飲料", _format_money(drink_total + addon_total))
    m3.metric("總金額", _format_money(total))

    order_lines = [
        f"{main_item} x {quantity} = {_format_money(item_total)}",
        f"飲料：{drink} = {_format_money(drink_total)}",
        f"加點：{', '.join(addons) if addons else '無'} = {_format_money(addon_total)}",
        f"取餐方式：{dining_type}",
        f"備註：{note or '無'}",
    ]
    st.code("\n".join(order_lines), language="text")

    action_col, reset_col = st.columns([1, 1])
    if action_col.button("送出訂單", type="primary", use_container_width=True):
        st.session_state.order_submitted = True
        st.rerun()
    if reset_col.button("清空狀態", use_container_width=True):
        st.session_state.order_submitted = False
        st.rerun()

    if st.session_state.order_submitted:
        st.success("訂單已送出。")

    extra = format_extra_context(
        "點餐 App",
        訂購人=customer or "（未填）",
        主餐=f"{main_item} x {quantity}",
        飲料=drink,
        加點=", ".join(addons) if addons else "無",
        取餐方式=dining_type,
        備註=note or "無",
        總金額=_format_money(total),
        訂單狀態="已送出" if st.session_state.order_submitted else "尚未送出",
    )

    st.markdown("#### 給 Agent 的摘要")
    st.code(extra, language="text")

    st.markdown("#### 右欄可以這樣問")
    st.markdown(
        """
- 「請幫我確認這張訂單，用一句話提醒總金額。」
- 「根據我的點餐內容，幫我推薦一個加點。」
- 「把訂單整理成店員看得懂的格式。」
"""
    )
    return extra


page_shell(
    "點餐 App",
    "練習用 Streamlit 做主餐、飲料、加點、數量與訂單摘要。",
    render_main,
    page_name="點餐 App",
)
