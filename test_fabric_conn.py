import os
import pyodbc
import struct
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential

load_dotenv()

SERVER = os.getenv("SERVER_MEDIA_TOOL")
DATABASE = os.getenv("DATABASE_MEDIA_TOOL")
CLIENT_ID = os.getenv("CLIENT_ID_AIAnalytics")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_AIAnalytics")
TENANT_ID = os.getenv("TENANT_ID", "common") # Need a proper tenant ID if possible, let's look for one

print(f"Server: {SERVER}")
print(f"Database: {DATABASE}")

# Test 1: ActiveDirectoryServicePrincipal built-in ODBC
print("\n--- Test 1: Native ODBC Service Principal ---")
conn_str_1 = (
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server={SERVER};"
    f"Database={DATABASE};"
    "Authentication=ActiveDirectoryServicePrincipal;"
    f"UID={CLIENT_ID};"
    f"PWD={CLIENT_SECRET};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=30;"
)

try:
    print("Connecting...")
    conn = pyodbc.connect(conn_str_1)
    print("Success Native ODBC!")
    conn.close()
except Exception as e:
    print(f"Failed Native ODBC: {e}")

# Test 2: Token-based
print("\n--- Test 2: Token injected ---")
# Let's try to get a token using ClientSecretCredential
# Assuming tenant is the standard one, wait, we don't have tenant ID in .env.
# Let's see if az login can provide DefaultAzureCredential
from azure.identity import DefaultAzureCredential
try:
    print("Getting token via DefaultAzureCredential...")
    credential = DefaultAzureCredential()
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("utf-16-le")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    
    conn_str_2 = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={SERVER};"
        f"Database={DATABASE};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    
    attrs_before = {1256: token_struct}
    conn = pyodbc.connect(conn_str_2, attrs_before=attrs_before)
    print("Success Token Auth!")
    conn.close()
except Exception as e:
    print(f"Failed Token Auth: {e}")
