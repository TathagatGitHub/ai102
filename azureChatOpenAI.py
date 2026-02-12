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
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
#project_connection_string = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")

llm = AzureChatOpenAI(
    azure_endpoint=azure_openai_endpoint,
    api_key=azure_openai_key,
    api_version="2025-01-01-preview",
    deployment_name="gpt-4.1"
)

# 2. Fabric Lakehouse Config (SQL Alchemy format)

SERVER = "qmmuvmirrmauboe46vi3s6b3um-5updb6opn2hu5awqmb5fgzzzgi.database.fabric.microsoft.com,1433"
DATABASE = "DemoSQLDatabase-f499435c-5bc1-4785-92c8-5015977d6d98"

# Service Principal Auth (from environment variables)
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Authentication=ActiveDirectoryServicePrincipal;"
    f"UID={CLIENT_ID};"
    f"PWD={CLIENT_SECRET};"
    "Encrypt=yes;"
    "Connection Timeout=180;"
    "Login Timeout=180;"
)
conn_str = f"mssql+pyodbc:///?odbc_connect={params}"



# 2. Connect to the Database
db = SQLDatabase.from_uri(conn_str)
print(f"DEBUG: db type: {type(db)}")
print(f"DEBUG: db name: {db.get_usable_table_names()}")  

# 3. Create the Agent (The "Brain")
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=True # This lets you see the SQL it generates in the console
)
# Fabric - : b14a1983-8b11-4001-b89c-f551b9783ba3
# Entra id - b14a1983-8b11-4001-b89c-f551b9783ba3
# 3b474170-3ebc-4c08-8120-dc6b08345bf5
# --- EXECUTION ---
query = "Show me all the buytypes which has buytypeid smaller than 2" # This is the natural language question you want to ask about your data
response = agent_executor.invoke(query)

print(f"Final Answer: {response['output']}")