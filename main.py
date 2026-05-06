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
    
    while True:
        user_input = input("You: ").strip()
        if user_input == "q" or user_input == "bye":
            print("bye")
            break
        print("Thinking...")
        print("AI: ", end="", flush=True)
        for chunk in llm.stream(user_input):
            print(chunk.content, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    main()
    
