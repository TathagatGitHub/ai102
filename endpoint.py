import os
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai import AzureOpenAI

project_endpoint = "https://leo-virgo-dec28th2025-resource.services.ai.azure.com/api/projects/leo-virgo-Dec28th2025"

api_key = os.environ.get("AZURE_API_KEY")

def build_client(cred):
    return AIProjectClient(credential=cred, endpoint=project_endpoint)

if api_key:
    credential = AzureKeyCredential(api_key)
else:
    credential = DefaultAzureCredential()

project_client = build_client(credential)

try:
    # List all connections in the project
    connections = project_client.connections
    print("List all connections:")
    for connection in connections.list():
        print("Connection:")
        print(f"{connection.name} ({connection.type})")

except Exception as ex:
    msg = str(ex)
    if api_key and ("get_token" in msg or isinstance(ex, AttributeError)):
        print("AZURE_API_KEY appears unsupported for this client; falling back to DefaultAzureCredential.")
        project_client = build_client(DefaultAzureCredential())
        connections = project_client.connections
        print("List all connections:")
        for connection in connections.list():
            print("Connection:")
            print(f"{connection.name} ({connection.type})")
    else:
        raise

# deployment name: gpt-5-chat-deploy01, version Model version 2025-10-03
try:
    
    # connect to the project
    project_endpoint = "https://leo-virgo-dec28th2025-resource.cognitiveservices.azure.com/"
    project_client = AIProjectClient(            
            credential=DefaultAzureCredential(),
            endpoint=project_endpoint,
        )
    
    # Get a chat client
    chat_client = project_client.get_openai_client()
    
    
    # Get a chat completion based on a user-provided prompt
    user_prompt = input("Enter a question:")
    
    response = chat_client.chat.completions.create(
       model="gpt-5-chat-deploy01",
       # model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": user_prompt}
        ]
    )
    print(response.choices[0].message.content)

except Exception as ex:
    print(ex)

