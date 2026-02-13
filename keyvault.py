from azure.keyvault.secrets import SecretClient
import os
import logging
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
load_dotenv()
credential = DefaultAzureCredential()
vault_url = os.environ["AZURE_VAULT_URL"]  

secret_name = "kv-webapp-st-secretkey"

secret_client = SecretClient(vault_url=vault_url, credential=credential)

secret=secret_client.get_secret(secret_name)

print ("Secret value: ", secret.value)
