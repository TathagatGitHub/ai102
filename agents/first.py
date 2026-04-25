import os
import time
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

load_dotenv()
print(os.getenv("GROQ_API_KEY"))
print(os.getenv("OPENWEATHER_API_KEY"))

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
    """Returns real current weather for a given city using OpenWeatherMap API."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        return f"Could not fetch weather for {city}: {data.get('message', 'Unknown error')}"

    temp        = data["main"]["temp"]
    feels_like  = data["main"]["feels_like"]
    humidity    = data["main"]["humidity"]
    description = data["weather"][0]["description"]
    wind        = data["wind"]["speed"]
    country     = data["sys"]["country"]

    return (
        f"Current weather in {city}, {country}: {description}. "
        f"Temperature: {temp}°C (feels like {feels_like}°C). "
        f"Humidity: {humidity}%. Wind speed: {wind} m/s."
    )

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
print(chat("What is the weather in London?"))