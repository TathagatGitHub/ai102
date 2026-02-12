# Azure & Fabric Hybrid Architecture Diagram

```mermaid
graph TD
    %% --- Styles ---
    classDef azure fill:#0078D4,stroke:#005A9E,stroke-width:2px,color:white;
    classDef fabric fill:#744DA9,stroke:#5C2D91,stroke-width:2px,color:white;
    classDef storage fill:#289556,stroke:#1E7145,stroke-width:2px,color:white;
    classDef security fill:#FFB900,stroke:#D83B01,stroke-width:2px,color:black;

    %% --- Azure Cloud Environment ---
    subgraph Azure_Cloud [Azure Cloud Platform]
        direction TB
        EntraID[("Entra ID (Azure AD)<br>Identity Provider")]:::security
        KeyVault[("Azure Key Vault<br>Secrets & Keys")]:::security
        
        WebApp[("Azure App Service<br>(.NET Web App)")]:::azure
        ADF[("Azure Data Factory<br>(Legacy ETL)")]:::azure
        FileShare[("Azure File Share<br>(Legacy SMB Drive)")]:::storage
        
        PowerAuto[("Power Automate<br>(Email Interceptor)")]:::azure
        AzureAI[("Azure AI Content<br>Understanding")]:::azure
    end

    %% --- Microsoft Fabric Environment ---
    subgraph Fabric_Cloud [Microsoft Fabric]
        direction TB
        
        subgraph OneLake_Storage [OneLake - Unified Storage]
            LakeFiles[("Lakehouse Files<br>(Bronze/Raw)")]:::storage
            LakeTables[("Lakehouse Tables<br>(Silver/Gold)")]:::storage
            MirroredData[("Mirrored SQL Data<br>(Delta Parquet)")]:::storage
        end
        
        FabricSQL[("Fabric SQL Database<br>(Transactional ODS)")]:::fabric
        FabPipeline[("Fabric Data Pipeline<br>(Copy Activity)")]:::fabric
        Notebook[("Fabric Notebook<br>(PySpark Compute)")]:::fabric
        PowerBI[("Power BI<br>(Reporting)")]:::fabric
    end

    %% --- Connections & Handshakes ---
    
    %% 1. Identity & Security
    EntraID -.->|Auth/Managed ID| WebApp
    EntraID -.->|Auth/Managed ID| ADF
    EntraID -.->|Auth| FabricSQL
    KeyVault -.->|Secrets| ADF
    KeyVault -.->|Secrets| FabPipeline

    %% 2. Web App Flow
    WebApp -->|SQL w/Managed ID| FabricSQL
    FabricSQL -.->|Zero-Copy Mirror| MirroredData

    %% 3. File Share Sync
    FileShare -->|SMB Read| FabPipeline
    FabPipeline -->|Write Files| LakeFiles

    %% 4. ADF Legacy Flow
    ADF -->|ADLS Gen2 API| LakeFiles

    %% 5. AI / Email Flow
    PowerAuto -->|REST Put| LakeFiles
    LakeFiles -->|Read Blob| AzureAI
    AzureAI -->|JSON Output| Notebook
    Notebook -->|Insert/Merge| FabricSQL

    %% 6. Analytics & Reporting
    MirroredData -.->|Shortcut| LakeTables
    LakeTables -->|Direct Lake| PowerBI

    %% --- Layout Adjustments ---
    linkStyle default stroke-width:2px,fill:none,stroke:gray;
```

## Architecture Flow

- **Entra ID**: Manages identity and authentication across Azure & Fabric
- **Key Vault**: Stores secrets and connection strings securely
- **Web App**: Legacy .NET application with managed identity auth
- **Data Factory**: Legacy ETL processes and data movement
- **Power Automate**: Automated workflow for email interception
- **Azure AI**: Content understanding and document processing
- **OneLake**: Unified storage layer (Bronze/Silver/Gold layers)
- **Fabric SQL**: Transactional database with zero-copy mirroring
- **Fabric Pipeline**: Modern data pipeline for orchestration
- **Notebook**: PySpark compute for data transformation
- **Power BI**: Analytics and reporting layer
