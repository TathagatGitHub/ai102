from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentunderstanding.models import AnalyzeInput

# Setup


formUrl = "https://stdepaolachr178846422708.blob.core.windows.net/d16098cd-a8c1-407b-8239-975e2d216e17-azureml-blobstore/adswhizz.pdf?sp=r&st=2026-02-03T21:34:57Z&se=2026-02-04T05:49:57Z&spr=https&sv=2024-11-04&sr=b&sig=rJfoC3yA5aH1lNrR6TyJD%2F%2FabVUE0depXMAWuUpJYeA%3D"


import os
from dotenv import load_dotenv

load_dotenv()

# Content Understanding Client section
endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
key = os.getenv("CONTENTUNDERSTANDING_KEY")

content_understanding_client = ContentUnderstandingClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

result = content_understanding_client.begin_analyze(
    analyzer_id="prebuilt-invoice",
    inputs=[AnalyzeInput(url=formUrl)]
).result()  


# Use result
print("Analysis successful!")
import json
# Serialize the result to JSON to verify content
try:
    print(json.dumps(result.as_dict(), indent=2))
except Exception as e:
    print(f"Could not print as dict: {e}")
    # Fallback inspection
    print(dir(result))

