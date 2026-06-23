import azure.functions as func
import pyodbc
import json
import os
import logging
import re
import time

from datetime import datetime, date
from decimal import Decimal

app = func.FunctionApp(
    http_auth_level=func.AuthLevel.ANONYMOUS
)

MAX_QUERY_LENGTH = 10000
DEFAULT_ROW_LIMIT = 1000


def is_safe(query: str) -> bool:

    q = query.strip().upper()

    logging.info(
        f"VALIDATING QUERY: {q}"
    )

    blocked = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "EXEC",
        "EXECUTE",
        "MERGE",
        "TRUNCATE",
        "--",
        "/*",
        "*/"
    ]

    if not q.startswith("SELECT"):

        logging.warning(
            f"FAILED SELECT CHECK: {q[:200]}"
        )

        return False

    for keyword in blocked:

        if keyword in q:

            logging.warning(
                f"BLOCKED KEYWORD DETECTED: {keyword}"
            )

            return False

    return True


def extract_tables(query: str):

    matches = re.findall(
        r"(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)",
        query,
        re.IGNORECASE
    )

    return set(matches)


def tables_allowed(query: str) -> bool:

    tables = extract_tables(query)

    logging.info(
        f"TABLES DETECTED: {tables}"
    )

    if not tables:
        return False

    for table in tables:

        table = table.lower()

        # Special exception
        if table in ["crfaa_factfinanceaw_2","crfaa_dimproduct1aw", " crfaa_dimproductsubcategory1aw"]:
            continue

        # Standard AdventureWorks rule
        if (
            table.startswith("crfaa_")
            and table.endswith("aw")
        ):
            continue

        logging.warning(
            f"TABLE NOT ALLOWED: {table}"
        )

        return False

    return True


def apply_row_limit(query: str) -> str:

    if re.search(
        r"\bTOP\s+\d+\b",
        query,
        re.IGNORECASE
    ):
        return query

    return re.sub(
        r"^\s*SELECT",
        f"SELECT TOP {DEFAULT_ROW_LIMIT}",
        query,
        count=1,
        flags=re.IGNORECASE
    )


def json_safe(obj):

    if isinstance(
        obj,
        (datetime, date)
    ):
        return obj.isoformat()

    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, bytes):
        return obj.decode(
            "utf-8",
            errors="replace"
        )

    raise TypeError(
        f"Type {type(obj)} not serializable"
    )


@app.route(route="query-dataverse")
def query_dataverse(
    req: func.HttpRequest
) -> func.HttpResponse:

    try:

        raw_body = req.get_body().decode(
            "utf-8",
            errors="ignore"
        )

        logging.info(
            f"RAW BODY: {raw_body}"
        )

        body = req.get_json()

        query = body.get(
            "query",
            ""
        ).strip()

        logging.info(
            f"QUERY RECEIVED: {query}"
        )

        # Remove trailing semicolon
        query = query.rstrip(";").strip()

        if not query:

            return func.HttpResponse(
                json.dumps({
                    "error": "Query is required"
                }),
                mimetype="application/json",
                status_code=400
            )

        if len(query) > MAX_QUERY_LENGTH:

            return func.HttpResponse(
                json.dumps({
                    "error":
                    "Query exceeds maximum length"
                }),
                mimetype="application/json",
                status_code=400
            )

        if not is_safe(query):

            return func.HttpResponse(
                json.dumps({
                    "error":
                    "Only safe SELECT queries are permitted",
                    "query_received":
                    query
                }),
                mimetype="application/json",
                status_code=400
            )

        if not tables_allowed(query):

            return func.HttpResponse(
                json.dumps({
                    "error":
                    "One or more tables are not authorised",
                    "query_received":
                    query,
                    "tables_found":
                    list(extract_tables(query))
                }),
                mimetype="application/json",
                status_code=400
            )

        query = apply_row_limit(query)

        logging.info(
            f"FINAL QUERY: {query}"
        )

        client_id = os.environ["CLIENT_ID"]
        client_secret = os.environ["CLIENT_SECRET"]

        server = os.environ["DATAVERSE_SERVER"]
        database = os.environ["DATAVERSE_DATABASE"]

        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server={server};"
            f"Database={database};"
            "Authentication=ActiveDirectoryServicePrincipal;"
            f"UID={client_id};"
            f"PWD={client_secret};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        logging.info(
            "CONNECTING TO DATAVERSE"
        )

        start_time = time.time()

        conn = pyodbc.connect(
            conn_str,
            timeout=30,
            autocommit=True
        )

        cursor = conn.cursor()

        cursor.execute(query)

        cols = [
            col[0]
            for col in cursor.description
        ]

        rows = [
            dict(zip(cols, row))
            for row in cursor.fetchall()
        ]

        conn.close()

        execution_time = round(
            time.time() - start_time,
            3
        )

        logging.info(
            f"QUERY SUCCESSFUL. "
            f"ROWS RETURNED: {len(rows)}"
        )

        response = {
            "query": query,
            "count": len(rows),
            "execution_time_seconds":
                execution_time,
            "columns": cols,
            "rows": rows
        }

        return func.HttpResponse(
            json.dumps(
                response,
                default=json_safe
            ),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:

        logging.exception(
            "DATAVERSE QUERY EXECUTION FAILED"
        )

        return func.HttpResponse(
            json.dumps({
                "error": str(e)
            }),
            mimetype="application/json",
            status_code=500
        )