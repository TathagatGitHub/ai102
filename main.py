# Before running the sample:
#    pip install --pre azure-ai-projects>=2.0.0b1
#    pip install azure-identity
#
# To use an API key instead of DefaultAzureCredential, set the environment
# variable `AZURE_API_KEY` (macOS / Linux):
#    export AZURE_API_KEY="<your-api-key>"

import os
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition


user_endpoint = "https://leo-virgo-dec28th2025-resource.services.ai.azure.com/api/projects/leo-virgo-dec28th2025"

api_key = os.environ.get("AZURE_API_KEY")

def build_client_with_credential(cred):
    return AIProjectClient(endpoint=user_endpoint, credential=cred)

# Prefer API key if provided, otherwise use DefaultAzureCredential
if api_key:
    credential = AzureKeyCredential(api_key)
else:
    credential = DefaultAzureCredential()

project_client = build_client_with_credential(credential)

agent_name = "<your-agent-name>"
model_deployment_name = "<your-model-deployment-name>"

def run_sample(client):
    # Creates an agent, bumps the agent version if parameters have changed
    agent = client.agents.create_version(
        agent_name=agent_name,
        definition=PromptAgentDefinition(
            model=model_deployment_name,
            instructions="You are a storytelling agent. You craft engaging one-line stories based on user prompts and context.",
        ),
    )

    openai_client = client.get_openai_client()

    # Reference the agent to get a response
    response = openai_client.responses.create(
        input=[{"role": "user", "content": "Tell me a one line story"}],
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
    )

    print(f"Response output: {response.output_text}")


try:
    run_sample(project_client)
except Exception as ex:
    msg = str(ex)
    # If the credential was an API key and the SDK attempted to call get_token,
    # fall back to DefaultAzureCredential (TokenCredential)
    if api_key and ("get_token" in msg or isinstance(ex, AttributeError)):
        print("AZURE_API_KEY appears unsupported for this client; falling back to DefaultAzureCredential.")
        project_client = build_client_with_credential(DefaultAzureCredential())
        run_sample(project_client)
    else:
        raise


