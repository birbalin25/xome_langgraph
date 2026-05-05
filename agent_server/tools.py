"""SQL execution helper for querying Databricks Delta tables."""

import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

from agent_server.config import SQL_WAREHOUSE_ID

logger = logging.getLogger(__name__)

# Service principal workspace client for SQL queries
_sp_client = WorkspaceClient()


def _execute_sql(query: str) -> list[dict]:
    """Execute a SQL query against the configured warehouse and return results as list of dicts."""
    response = _sp_client.statement_execution.execute_statement(
        statement=query,
        warehouse_id=SQL_WAREHOUSE_ID,
        wait_timeout="30s",
    )
    if response.status.state != StatementState.SUCCEEDED:
        error_msg = response.status.error.message if response.status.error else "Unknown error"
        raise RuntimeError(f"SQL execution failed: {error_msg}")

    if not response.result or not response.result.data_array:
        return []

    columns = [col.name for col in response.manifest.schema.columns]
    rows = []
    for row_data in response.result.data_array:
        rows.append(dict(zip(columns, row_data)))
    return rows
