import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from dotenv import load_dotenv
import pyodbc
import urllib.parse

load_dotenv()

# Create an Azure AI Project client
project_connection_string = os.environ["PROJECT_CONNECTION_STRING"]
key = os.getenv("PROJECT_KEY")
credential = AzureKeyCredential(key) if key else DefaultAzureCredential()
project = AIProjectClient(
    endpoint=project_connection_string,
    credential=credential
)

# Get the pre-configured chat client from the project
# This returns an azure.ai.inference.ChatCompletionsClient or openai.AzureOpenAI client
# depending on the SDK version, but usually it's compatible with OpenAI's interface.
chat_client = project.get_openai_client()

api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL", '')
if not api_key:
  raise Exception("A key should be provided to invoke the endpoint")

client = ChatCompletionsClient(
    endpoint='https://aioceanappdev.openai.azure.com/openai/deployments/gpt-4.1',
    credential=AzureKeyCredential(api_key),
    
)

# Initialize ChatOpenAI with the client from the project
llm = ChatOpenAI(
    #client=chat_client,
    client=client,
    model="gpt-4.1",
    temperature=0,
)

# Initialize the database
# 2. Fabric Lakehouse Config (SQL Alchemy format)
SERVER = os.getenv("FABRIC_SERVER", "qmmuvmirrmauboe46vi3s6b3um-5updb6opn2hu5awqmb5fgzzzgi.database.fabric.microsoft.com,1433")
DATABASE = os.getenv("FABRIC_DATABASE", "DemoSQLDatabase")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
 
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"      
    "Authentication=ActiveDirectoryServicePrincipal;"
    f"UID={CLIENT_ID};"
    f"PWD={CLIENT_SECRET};"      
)
db = SQLDatabase.from_uri(f"mssql+pyodbc:///?odbc_connect={params}")

# Create the SQL agent
agent = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=True,
)

# Run the agent
agent.invoke("How many employees are there?")