import os
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import pyodbc
import urllib.parse

# --- CONFIGURATION ---
load_dotenv()

# Create an Azure AI Project client
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT_EMPOWEROCEAN_DEVFOUNDRY"]
#project_connection_string = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY_EMPOWER_DEVFOUNDRY")



llm = AzureChatOpenAI(
    azure_endpoint=azure_openai_endpoint,
    api_key=azure_openai_key,
    api_version="2025-01-01-preview",
    deployment_name="gpt-4.1"
)

# 2. Fabric Lakehouse Config (SQL Alchemy format)

SERVER = os.getenv("SERVER_MEDIA_TOOL")
DATABASE = os.getenv("DATABASE_MEDIA_TOOL")

# Service Principal Auth (from lanchainopenaisql-projecthub.py)
# Instead of Native ODBC Auth, we use DefaultAzureCredential to get a token and pass it to SQLAlchemy
import struct

credential = DefaultAzureCredential()
token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("utf-16-le")
token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=30;"
)
conn_str = f"mssql+pyodbc:///?odbc_connect={params}"

# Define custom table info for better LLM context
custom_table_info = {
    "config_data_migration": (
        "A table of config_data_migration.\n"
    )
}
# 
from sqlalchemy import create_engine
engine = create_engine(
    conn_str,
    connect_args={
        "attrs_before": {1256: token_struct}
    }
)

# 2. Connect to the Database
db = SQLDatabase(engine=engine,custom_table_info=custom_table_info)
print(f"DEBUG: db name: {db.get_usable_table_names()}")

# 3. Create the Agent (The "Brain")
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
   # schema="dm", 
    agent_type="openai-tools",
    verbose=True # This lets you see the SQL it generates in the console
)
# Fabric - : b14a1983-8b11-4001-b89c-f551b9783ba3
# Entra id - b14a1983-8b11-4001-b89c-f551b9783ba3
# 3b474170-3ebc-4c08-8120-dc6b08345bf5
# --- EXECUTION ---
query = "select * from dm.config_data_migration" # This is the natural language question you want to ask about your data
response = agent_executor.invoke(query)

print(f"Final Answer: {response['output']}")