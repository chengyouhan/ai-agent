import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage

def main():
    name = "AI Agent"
    print("Hello from ai-agent!")
    print(f"My name is {name}")
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        print("OPENAI_API_KEY is set")
    else:
        print("OPENAI_API_KEY is not set")
        return

    llm = ChatOpenAI(
        model = os.getenv("MODEL"),
        temperature = float(os.getenv("TEMPERATURE", 0.5)),
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    messages = []
    while True:
        user_input = input("You: ").strip()
        if user_input == "q" or user_input == "bye":
            print("bye")
            break

        human_message= HumanMessage(content=user_input)
        context_message = [*messages,human_message]
        
        print("Thinking...")
        print("AI: ", end="", flush=True)
        reply_parts: list[str] = []
        for chunk in llm.stream(context_message):
            print(chunk.content, end="", flush=True)
            reply_parts.append(chunk.content)
        print()
        assistant_text = "".join(reply_parts)
        assistant_message = AIMessage(content=assistant_text)
        messages.append(human_message)
        messages.append(assistant_message)
    
if __name__ == "__main__":
    main()
    
