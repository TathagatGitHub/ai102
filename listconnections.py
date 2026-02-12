import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()

project_connection_string = os.environ["PROJECT_CONNECTION_STRING"]

# AIProjectClient requires a TokenCredential, not AzureKeyCredential
credential = DefaultAzureCredential()

# Your existing string: "eastus.api...;subscription_id=...;resource_group=...;project_name=..."
conn_str = project_connection_string    


# Parse the string
details = dict(item.split('=') for item in conn_str.split(';') if '=' in item)

project = AIProjectClient(
    endpoint=conn_str,
    credential=credential
)
# 2. Ask the Manager for the specific deployment details

print("Available connections in the project:")
connections_list = []
for conn in project.connections.list():
    print(f" - {conn.name} ({conn.type})")
    connections_list.append(conn)

if not connections_list:
    print("ERROR: No connections found in the project!")
    exit(1)

# Find an OpenAI or APIKey connection (not KeyVault)
openai_connection = None
for conn in connections_list:
    if conn.type in ["OpenAI", "AzureOpenAI", "Serverless"]:
        openai_connection = project.connections.get(name=conn.name)
        print(f"Using connection: {openai_connection.name} ({openai_connection.type})")
        break

if not openai_connection:
    print("ERROR: No OpenAI connection found. Available types:")
    for conn in connections_list:
        print(f"  - {conn.name} ({conn.type})")
    print("\nUsing project's OpenAI client instead...")
    
    # Get the OpenAI client directly from the project
    chat_client = project.get_openai_client()
    llm = ChatOpenAI(
        client=chat_client,
        model="gpt-4o",
    )
else:
    # 3. Initialize the Worker (LangChain) using details from the Manager
    llm = AzureChatOpenAI(
        azure_endpoint=openai_connection.endpoint_url,
        api_key=openai_connection.key, # If using key-based auth
        # Or rely on DefaultAzureCredential if api_key is omitted
        deployment_name="gpt-4o",
        api_version="2024-05-01-preview"
    )

print("Success! Your project is now connected.")
print(f"Chat client initialized: {type(chat_client)}\n")

# Test the connection by making a simple API call
try:
    # Try different model names
    models_to_try = ["gpt-4o", "gpt-4", "gpt-35-turbo", "gpt-4-turbo"]
    response = None
    
    for model in models_to_try:
        try:
            print(f"Trying model: {model}...", end=" ")
            response = chat_client.chat.completions.create(
                messages=[{"role": "user", "content": "Say 'Connection successful!'"}],
                model=model,
            )
            print("✓ SUCCESS")
            break
        except Exception as e:
            print(f"✗ Failed ({str(e)[:30]})")
    
    if response:
        print(f"\nAPI Response: {response.choices[0].message.content}")
    else:
        print("None of the default models worked. Check your Azure AI Project deployments.")
        
except Exception as e:
    print(f"Error: {e}")