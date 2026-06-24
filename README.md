#AdventureWorks AI Financial Agent/ ERP Analyst

An AI-powered financial analytics agent built on Microsoft Copilot Studio, 
capable of querying the AdventureWorks Data Warehouse via natural language 
and generating downloadable financial reports. Developed to be used within an ERP Management System by ERP managers.

## Demo
Watch the demo: https://youtu.be/aeBjRsxCiGA 

## What It Does
- Accepts natural language financial queries from business users
- Routes simple queries to a Dataverse MCP server and complex 
  analytical queries to an Azure Function with full T-SQL support
- Generates formatted HTML/PDF financial reports stored in SharePoint
- Returns a 24-hour SAS link to the report directly in chat

## Architecture
User → Copilot Studio Agent (No Auth, iframe embedded)
  ├── Simple queries → Dataverse MCP Server (read_query)
  └── Complex queries → Azure Function (pyodbc → Dataverse TDS endpoint)
           → Power Automate flow
           → SharePoint report generation
           → Blob Storage SAS URL
           → Report link returned in chat

## Reports Supported
- Budget vs Actual Variance (Q/Y, by department/organization)
- Balance Sheet (FY, Actual scenario)
- Sales Quota Attainment (by rep, by year)
- Internet vs Reseller Channel Comparison
- Inventory Level & Low Stock Alerts
- Customer Loyalty Segmentation
- Department Spend Analysis
- Profit vs Loss
- Product Sales Tracking
  

## Tech Stack
| Component | Technology |
|------------|------------|
| **AI Agent** | Microsoft Copilot Studio |
| **Data Store** | Microsoft Dataverse (AdventureWorks DW tables) |
| **Query Engine** | Azure Function (Python, pyodbc, Dataverse TDS Endpoint) |
| **Authentication** | Microsoft Entra ID Service Principal (Client Credentials Flow) |
| **Report Generation** | Power Automate, SharePoint, Azure Blob Storage |
| **Frontend** | Microsoft Power Pages, Static HTML Portal |
| **Source Data** | AdventureWorks DW 2022 (30 tables imported via Dataverse Dataflows) |
| **Schema Intelligence** | Custom AdventureWorks DW Join Map & Schema Prompt |
| **Tool Orchestration** | MCP Server + Custom Connector |
| **Data Access Method** | SQL over Dataverse TDS Endpoint |

## Architecture
User
  ↓
Power Pages Portal
  ↓
Copilot Studio Agent
  ↓
MCP Server
  ↓
Describe Tool (Schema Discovery)
  ↓
SQL Query Generation
  ↓
Azure Function (Python)
  ↓
Dataverse TDS Endpoint
  ↓
AdventureWorks DW Tables
  ↓
Power Automate
  ↓
SharePoint / Blob Storage Report Output

## Key Technical Decisions
- Used Dataverse TDS endpoint over Web API for full T-SQL support 
  (CASE, GROUP BY, multi-table JOINs, subqueries)
- Discovered and resolved datekey type mismatch between FactFinance 
  (integer) and DimDate (string) requiring CAST in all date joins
- Implemented instruction-based table scoping as security layer since 
  built-in Dataverse MCP cannot be restricted by code
- Used No Auth agent configuration for iframe embedding, with Azure 
  Function handling Dataverse auth independently via service principal

## Details
See AdventureWorks Documentation in the Documents Folder for full details and the Example Reports folder for sample reports.
