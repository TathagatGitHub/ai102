# pylint: disable=line-too-long,useless-suppression
# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------
"""
FILE: sample_analyze_return_raw_json.py

DESCRIPTION:
    This sample demonstrates how to access the raw JSON response from analysis operations
    using the convenience method and then accessing the raw response. This is useful for
    scenarios where you need to inspect the full response structure exactly as returned by
    the service.

    The Content Understanding SDK provides a convenient object model approach (shown in
    sample_analyze_binary.py) that returns AnalyzeResult objects with deeper navigation
    through the object model. However, sometimes you may need access to the raw JSON
    response for:

    - Easy inspection: View the complete response structure in the exact format returned
      by the service, making it easier to understand the full data model and discover
      available fields
    - Debugging: Inspect the raw response to troubleshoot issues, verify service behavior,
      or understand unexpected results
    - Advanced scenarios: Work with response structures that may change or include
      additional metadata not captured in the typed model

    NOTE: For most production scenarios, the object model approach is recommended as it
    provides type safety, IntelliSense support, and easier navigation. Use raw JSON access
    when you specifically need the benefits listed above.

USAGE:
    python sample_analyze_return_raw_json.py

    Set the environment variables with your own values before running the sample:
    1) CONTENTUNDERSTANDING_ENDPOINT - the endpoint to your Content Understanding resource.
    2) CONTENTUNDERSTANDING_KEY - your Content Understanding API key (optional if using DefaultAzureCredential).

    Before using prebuilt analyzers, you MUST configure model deployments for your Microsoft Foundry
    resource. See sample_update_defaults.py for setup instructions.
"""

import json
import os

from dotenv import load_dotenv
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.contentunderstanding.models import AnalyzeInput

load_dotenv()


def main() -> None:
    endpoint = os.environ["CONTENTUNDERSTANDING_ENDPOINT"]
    key = os.getenv("CONTENTUNDERSTANDING_KEY")
    credential = AzureKeyCredential(key) if key else DefaultAzureCredential()

    client = ContentUnderstandingClient(endpoint=endpoint, credential=credential)

    # [START analyze_return_raw_json]
    file_path = "invoice/adswhizz.pdf"

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        print(f"File size: {len(file_bytes)} bytes")

    print(f"Analyzing {file_path} with prebuilt-documentSearch...")
    # formUrl = "https://stdepaolachr178846422708.blob.core.windows.net/d16098cd-a8c1-407b-8239-975e2d216e17-azureml-blobstore/adswhizz.pdf?sp=r&st=2026-02-03T21:34:57Z&se=2026-02-04T05:49:57Z&spr=https&sv=2024-11-04&sr=b&sig=rJfoC3yA5aH1lNrR6TyJD%2F%2FabVUE0depXMAWuUpJYeA%3D"

    formUrl = "https://stdepaolachr178846422708.blob.core.windows.net/d16098cd-a8c1-407b-8239-975e2d216e17-azureml-blobstore/adswhizz.pdf?sp=r&st=2026-02-05T20:59:18Z&se=2026-02-06T05:14:18Z&spr=https&sv=2024-11-04&sr=b&sig=6GD%2Bk49xg28Ndw5ZcqJlQEoawZUjBRk6CTOzwVIwR74%3D"
    # Use the convenience method to analyze the document
    # The cls callback allows access to the complete response structure for easy inspection and debugging
    # URL Version
    poller = client.begin_analyze(
        analyzer_id="prebuilt-layout",
        inputs=[AnalyzeInput(url=formUrl)],
        cls=lambda pipeline_response, deserialized_obj, response_headers: (
            deserialized_obj,
            pipeline_response.http_response,
        ),
    )
    # Binary Version
    # poller = client.begin_analyze_binary(
    #     analyzer_id="prebuilt-layout",
    #     binary_input=file_bytes,
    #     cls=lambda pipeline_response, deserialized_obj, response_headers: (
    #         deserialized_obj,
    #         pipeline_response.http_response,
    #     ),
    # )

    # Wait for completion and get both the deserialized object and raw HTTP response
    _, raw_http_response = poller.result()
    # [END analyze_return_raw_json]

    # [START parse_raw_json]
    # Get the raw JSON response
    response_json = raw_http_response.json()

    # Pretty-print the raw JSON response
    pretty_json = json.dumps(response_json, indent=2, ensure_ascii=False)
    # print(pretty_json)

    # Store the raw JSON response to a file for further analysis if needed
    output_file = "raw_response_documentSearch.json"

    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write(pretty_json)

    # [END parse_raw_json]


if __name__ == "__main__":
    main()
 