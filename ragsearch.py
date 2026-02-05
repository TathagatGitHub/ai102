import os
from openai import AzureOpenAI

# Load credentials and endpoints from environment for safety
API_KEY = os.environ.get("AZURE_API_KEY")
# Base OpenAI resource endpoint (no path/query)
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT",
    "https://leo-virgo-dec28th2025-resource.openai.azure.com"
)

# Get an Azure OpenAI chat client
chat_client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=API_KEY,
)

# Initialize prompt with system message
prompt = [
    {"role": "system", "content": "You are a helpful AI assistant."}
]

# Add a user input message to the prompt

input_text = input("Enter a question: ")
prompt.append({"role": "user", "content": input_text})

# Additional parameters to apply RAG pattern using the AI Search index
# Only build RAG params when a valid Azure Cognitive Search endpoint is provided
search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "").strip()
if search_endpoint and "<" not in search_endpoint:
    rag_params = {
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": search_endpoint,
                    "index_name": os.environ.get("AZURE_SEARCH_INDEX", "gentle-roof-z79qr8lpcd"),
                    "authentication": {
                        "type": "api_key",
                        "key": os.environ.get("AZURE_SEARCH_KEY", ""),
                    },
                    "query_type": "vector",
                    "embedding_dependency": {
                        "type": "deployment_name",
                        "deployment_name": os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002-deployment"),
                    },
                }
            }
        ],
    }
else:
    rag_params = None

# Submit the prompt with the index information
# Submit the prompt, include RAG params only when available
create_kwargs = {
    "model": os.environ.get("AZURE_CHAT_DEPLOYMENT", "gpt-5-chat-deploy01"),
    "messages": prompt,
}
if rag_params:
    create_kwargs["extra_body"] = rag_params

response = chat_client.chat.completions.create(**create_kwargs)

# Print the contextualized response
completion = response.choices[0].message.content
print(completion)