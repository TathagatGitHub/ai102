import os
import time
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

load_dotenv()

# 1. Initialize the LLM
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
)

# 2. Define tools
@tool
def add_numbers(a: float, b: float) -> float:
    """Adds two numbers together."""
    return a + b

@tool
def get_weather(city: str) -> str:
    """Returns real current weather for a given city."""
    # wttr.in is a free weather service — no API key needed
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url, headers={"User-Agent": "curl/7.68.0"})
    
    if response.status_code == 200:
        return response.text.strip()
    else:
        return f"Could not fetch weather for {city}."

# 3. Create the agent
agent = create_react_agent(
    model=llm,
    tools=[add_numbers, get_weather],
)

# 4. Run the agent
def chat(user_input: str):
    response = agent.invoke({
        "messages": [HumanMessage(content=user_input)]
    })
    return response["messages"][-1].content

# --- EXAMPLES ---
print(chat("What is 42 + 58?"))
time.sleep(3)
print(chat("What is the weather in Tokyo?"))
time.sleep(3)
print(chat("What is the weather in Buena Park, CA?"))