
import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ.get("OPENAI_ENDPOINT")
api_key = os.environ.get("OPENAI_API_KEY")
print(f"Connecting to endpoint: {endpoint}")

try:
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-05-01-preview",
    )

    print("Listing deployments (models)...")
    # In Azure OpenAI, 'models' list usually returns available models, but we need deployments.
    # However, the standard list_models() often returns deployments or base models depending on the version.
    models = client.models.list()
    for model in models:
        print(f" - ID: {model.id}, Created: {model.created}, Owned By: {model.owned_by}")

except Exception as e:
    print(f"Error listing models: {e}")
