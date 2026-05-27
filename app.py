import shutil
import asyncio
from pathlib import Path
import chainlit as cl
from agent_core import Agent

@cl.on_chat_start
async def start():
    """當對話開始時，初始化 Agent 並存入 session。"""
    agent = Agent.from_env()
    cl.user_session.set("agent", agent)
    cl.user_session.set("image_path", None)
    await cl.Message(content="你好！我是法鬥超人。你可以跟我聊天，也可以上傳圖片給我看喔！").send()

@cl.on_message
async def main(message: cl.Message):
    """處理使用者訊息，並使用 Agent.chat 進行串流輸出。"""
    agent = cl.user_session.get("agent")
    image_path = cl.user_session.get("image_path")
    
    # --- 處理圖片上傳邏輯 ---
    if message.elements:
        for element in message.elements:
            if element.type == "image":
                upload_dir = Path(".files")
                upload_dir.mkdir(exist_ok=True)
                temp_path = upload_dir / f"temp_{element.name}"
                shutil.copy(element.path, temp_path)
                image_path = temp_path.as_posix()
                cl.user_session.set("image_path", image_path)
                await cl.Message(content=f"已收到圖片：{element.name}").send()
                await cl.Message(
                    content="",
                    elements=[cl.Image(name=element.name, path=str(temp_path))],
                ).send()

    # 建立一個 Chainlit 的 Message 物件，用於串流顯示
    msg = cl.Message(content="")
    await msg.send()

    # 定義 on_token 回呼函式
    # 這裡我們使用 loop.call_soon_threadsafe 來確保在同步執行緒中也能安全地更新 UI
    loop = asyncio.get_event_loop()

    def on_token_callback(token: str):
        # msg.stream_token is async; schedule it back onto Chainlit's event loop
        # from the worker thread and wait so tokens stay in order.
        future = asyncio.run_coroutine_threadsafe(msg.stream_token(token), loop)
        future.result()

    try:
        # 關鍵修正：使用 asyncio.to_thread 將同步的 agent.chat 放到另一個執行緒執行
        # 這樣才不會阻塞 Chainlit 的主事件迴層，讓 stream_token 有機會即時反應
        await asyncio.to_thread(
            agent.chat,
            user_text=message.content,
            image_path=image_path,
            on_token=on_token_callback
        )
        
        cl.user_session.set("image_path", None)
        
    except Exception as e:
        await cl.Message(content=f"發生錯誤：{str(e)}").send()
    finally:
        await msg.update()

if __name__ == "__main__":
    pass
