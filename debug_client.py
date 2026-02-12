
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

project_connection_string = os.environ["PROJECT_CONNECTION_STRING"]
key = os.getenv("PROJECT_KEY")
credential = AzureKeyCredential(key) if key else DefaultAzureCredential()

try:
    project = AIProjectClient(
        endpoint=project_connection_string,
        credential=credential
    )
    client = project.get_openai_client()
    print(f"Type of client: {type(client)}")
    print(f"Dir of client: {dir(client)}")
    
    if hasattr(client, 'chat'):
        print(f"Client has 'chat' attribute: {type(client.chat)}")
        if hasattr(client.chat, 'completions'):
            print(f"Client.chat has 'completions' attribute: {type(client.chat.completions)}")
            if hasattr(client.chat.completions, 'create'):
                print("Client.chat.completions has 'create' method.")
            else:
                print("Client.chat.completions MISSING 'create' method.")
        else:
             print("Client.chat MISSING 'completions' attribute.")
    else:
        print("Client MISSING 'chat' attribute.")

except Exception as e:
    print(f"Error: {e}")
