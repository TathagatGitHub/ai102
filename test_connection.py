import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

SERVER = os.getenv('SERVER_MEDIA_TOOL')
DATABASE = os.getenv('DATABASE_MEDIA_TOOL')
CLIENT_ID = os.getenv('CLIENT_ID_AIAnalytics')
CLIENT_SECRET = os.getenv('CLIENT_SECRET_AIAnalytics')

print(f"Testing connection to: {SERVER}")
print(f"Database: {DATABASE}")

conn_str = f"Driver={{ODBC Driver 18 for SQL Server}};Server={SERVER};Database={DATABASE};UID={CLIENT_ID};PWD={CLIENT_SECRET};Authentication=ActiveDirectoryServicePrincipal;Encrypt=yes;"

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    print("✓ Connection successful!")
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
