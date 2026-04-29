import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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
    
    response = llm.invoke("用一句繁體中文自我介紹。")
    print(response.content)


if __name__ == "__main__":
    main()
    
