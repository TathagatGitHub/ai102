import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENWEATHER_API_KEY")
url = f"https://api.openweathermap.org/data/2.5/weather?q=Tokyo&appid={api_key}&units=metric"

response = requests.get(url)
print(api_key)
print(f"Status: {response.status_code}")
print(response.json())