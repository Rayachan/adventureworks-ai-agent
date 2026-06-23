import azure.functions as func
import pyodbc, json, os, logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

ALLOWED_TABLES = {
    "crfaa_factfinanceaw", "crfaa_dimaccountaw", "crfaa_dimdateaw",
    "crfaa_dimorganizationaw", "crfaa_dimscenarioaw",
    "crfaa_dimdepartmentgroupaw",
    # ...rest of your 15-table allowlist
}

def is_safe(query: str) -> bool:
    q = query.strip().upper()
    blocked = ["INSERT","UPDATE","DELETE","DROP","EXEC","--",";","TRUNCATE"]
    return q.startswith("SELECT") and not any(k in q for k in blocked)

def tables_allowed(query: str) -> bool:
    q = query.upper()
    return any(t.upper() in q for t in ALLOWED_TABLES)

@app.route(route="query-dataverse")
def query_dataverse(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body  = req.get_json()
        query = body.get("query", "").strip()

        if not query or not is_safe(query) or not tables_allowed(query):
            return func.HttpResponse(json.dumps({"error": "Invalid or unauthorised query"}), status_code=403)

        tenant_id     = os.environ["TENANT_ID"]
        client_id     = os.environ["CLIENT_ID"]
        client_secret = os.environ["CLIENT_SECRET"]
        server        = os.environ["DATAVERSE_SERVER"]   # e.g. org48bde522.api.crm.dynamics.com,5558
        database      = os.environ["DATAVERSE_DATABASE"] # e.g. org48bde522

        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server={server};Database={database};"
            "Authentication=ActiveDirectoryServicePrincipal;"
            f"UID={client_id};PWD={client_secret};"
            "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )

        conn = pyodbc.connect(conn_str, timeout=30, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        conn.close()

        return func.HttpResponse(json.dumps({"columns": cols, "rows": rows, "count": len(rows)}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)