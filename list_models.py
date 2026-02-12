import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from langchain_azure_ai import ChatAzureAI
from dotenv import load_dotenv

load_dotenv()

project_connection_string = os.environ["PROJECT_CONNECTION_STRING"]
credential = DefaultAzureCredential()


try:
    project = AIProjectClient(
        endpoint=project_connection_string,
        credential=credential
    )
    
    # Get the OpenAI client from the project
    chat_client = project.get_openai_client()
    
    print("Listing available models...")
    print(f"Chat client type: {type(chat_client)}")
    
    # Try to list models - this may not be available on all endpoints
    try:
        models = chat_client.models.list()
        print("Available models:")
        for model in models:
            print(f" - {model.id}")
    except Exception as model_error:
        print(f"Models endpoint not available: {model_error}")
        print("\nNote: Some Azure AI Project endpoints don't expose the /models endpoint.")
        print("Check your Azure portal for available deployments.")

except Exception as e:
    print(f"Error: {e}")
    print(f"\nTroubleshooting:")
    print(f"1. Check PROJECT_CONNECTION_STRING is correct: {project_connection_string[:50]}...")
    print(f"2. Verify you're authenticated with the correct tenant/subscription")
    print(f"3. Use: az account show --query tenantId")
