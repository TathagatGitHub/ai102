import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# ============================================
# Configuration
# ============================================
load_dotenv()
OM_FOUNDRY_PROJECT_ENDPOINT = os.getenv("OM_FOUNDRY_PROJECT_ENDPOINT")
OM_FOUNDRY_DEFAULT_PRO_ENDPOINT = os.getenv("OM_FOUNDRY_DEFAULT_PRO_ENDPOINT")

# Authentication Option A: Using Azure AD (Managed Identity/Service Principal)
credential = DefaultAzureCredential()

# Authentication Option B: Using API Key (if you have one)
# API_KEY = "your-api-key-here"
# credential = AzureKeyCredential(API_KEY)

# ============================================
# Initialize AI Project Client
# ============================================
project_client = AIProjectClient(
    #endpoint=OM_FOUNDRY_PROJECT_ENDPOINT,   
    endpoint=OM_FOUNDRY_DEFAULT_PRO_ENDPOINT,
    credential=credential
)

# ============================================
# List All Deployments (Models)
# ============================================
print("Fetching deployed models...\n")

try:
    # Get all deployments
    deployments = project_client.deployments.list()  # This may return a paged response depending on the SDK version
    
    print(f"{'='*80}")
    print(f"DEPLOYED MODELS IN PROJECT")
    print(f"{'='*80}\n")
    
    for i, deployment in enumerate(deployments, 1):
        print(f"Model {i}:")
        print(f"  Deployment Name: {deployment.name}")
        print(f"  Model Name: {deployment.model_name if hasattr(deployment, 'model_name') else 'N/A'}")
        print(f"  Model Version: {deployment.model_version if hasattr(deployment, 'model_version') else 'N/A'}")
        print(f"  SKU: {deployment.sku.name if hasattr(deployment, 'sku') else 'N/A'}")
        print(f"  Capacity: {deployment.sku.capacity if hasattr(deployment, 'sku') else 'N/A'}")
        print(f"  Status: {deployment.provisioning_state if hasattr(deployment, 'provisioning_state') else 'N/A'}")
        print(f"  Created: {deployment.created_at if hasattr(deployment, 'created_at') else 'N/A'}")
        print(f"  Endpoint: {deployment.endpoint_uri if hasattr(deployment, 'endpoint_uri') else 'N/A'}")
        print(f"{'-'*80}\n")
    
    # Store deployment names for later use
    deployment_names = [d.deployment_name for d in deployments]
    print(f"\nAvailable deployment names: {deployment_names}")
    
except Exception as e:
    print(f"Error listing deployments: {e}")
    print(f"Error type: {type(e).__name__}")