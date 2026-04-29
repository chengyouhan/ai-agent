import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()
os.getenv("OPENAI_API_KEY","Hello")

def main():
    name = "AI Agent"
    print("Hello from ai-agent!")
    print(f"My name is {name}")
    print(os.getenv("OPENAI_API_KEY"))
    print(os.getenv("Hello","OPENAI_API_KEY"))

if __name__ == "__main__":
    main()
