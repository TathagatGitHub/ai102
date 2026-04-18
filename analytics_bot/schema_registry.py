"""
Schema registry for the Azure Fabric Lakehouse.
Maps each SQL schema name (lowercase, as it appears in INFORMATION_SCHEMA)
to a plain-English description used by the intent classifier when selecting
which schemas to introspect for a given question.
"""

SCHEMA_REGISTRY: dict = {
    "claritas":    "Claritas demographic and audience ratings data — audience segments, Nielsen/Claritas data",
    "dbo":         "Core operational data — postlogs, broadcast records, programmes, airings, core business tables",
    "dbbudget":    "Budget planning, forecasts, budget revisions, and spend tracking",
    "dcm":         "Digital Campaign Manager (DCM) — digital ad trafficking, placements, and digital campaign data",
    "dm":          "Data migration tables — configuration tables used during ETL and data migration processes",
    "estimp":      "Media estimates and impressions — CPM, GRP, impressions estimates by market and demo",
    "finance":     "Financial records — revenue, billing, reconciliation, and financial reporting",
    "invoices":    "Invoice records — accounts payable, accounts receivable, invoice line items",
    "traffic":     "Traffic management — scheduling instructions, spot placement, copy rotation, traffic orders",
    "map":         "Mapping and cross-reference tables — market maps, station maps, product mappings, lookup data",
    "podcast":     "Podcast content — episodes, feeds, downloads, performance metrics, podcast ad placements",
    "podinvoices": "Podcast invoice records — billing and invoices specific to podcast advertising",
    "radiolog":    "Radio broadcast logs — radio air check data, logged spots, discrepancy reporting",
    "response":    "Response tracking — direct response (DR) metrics, call volumes, campaign response rates",
}
