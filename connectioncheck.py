# pip install azure-ai-inference
import os
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL", '')
if not api_key:
  raise Exception("A key should be provided to invoke the endpoint")

client = ChatCompletionsClient(
    endpoint='https://aioceanappdev.openai.azure.com/openai/deployments/gpt-4.1',
    credential=AzureKeyCredential(api_key),
    
)

payload = {
  "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain Azure AI Inference SDK in simple terms."}
    ],
  "temperature": 1,
  "top_p": 1,
  "stop": [],
  "frequency_penalty": 0,
  "presence_penalty": 0
}
response = client.complete(payload)

print("Response:", response.choices[0].message.content)
print("Model:", response.model)
print("Usage:")
print(" Prompt tokens:", response.usage.prompt_tokens)
print(" Total tokens:", response.usage.total_tokens)
print(" Completion tokens:", response.usage.completion_tokens)
 