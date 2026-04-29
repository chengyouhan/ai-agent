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

if __name__ == "__main__":
    main()
    
