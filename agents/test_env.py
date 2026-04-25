import os
from dotenv import load_dotenv, find_dotenv
print("load_dotenv():", load_dotenv())
print("GROQ_API_KEY:", os.getenv("GROQ_API_KEY"))
print("CONTENTUNDERSTANDING_ENDPOINT:", os.getenv("CONTENTUNDERSTANDING_ENDPOINT"))
