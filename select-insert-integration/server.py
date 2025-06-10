from mcp.server.fastmcp import FastMCP
import psycopg2
import psycopg2.extras
import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import sys

# Import the structured tools
from insert_tool import mcp_insert_tool
from select_tool import mcp_select_tool

# Initialize the MCP server
mcp = FastMCP("Enhanced PostgreSQL Database Server")

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'database': 'test_database',
    'user': 'postgres',
    'password': '12345678',
    'port': 5432
}

# Configuration
QUERY_TIMEOUT = 30
MAX_ROWS = 1000
RESTRICTED_MODE = False

def get_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DB_CONFIG)

def is_safe_query(query: str) -> Tuple[bool, str]:
    """Check if a query is safe to execute in restricted mode."""
    if not RESTRICTED_MODE:
        return True, ""

    query_upper = query.strip().upper()
    dangerous_operations = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
        'TRUNCATE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
    ]

    for operation in dangerous_operations:
        if query_upper.startswith(operation):
            return False, f"Operation '{operation}' not allowed in restricted mode"

    dangerous_functions = ['pg_terminate_backend', 'pg_cancel_backend']
    for func in dangerous_functions:
        if func.upper() in query_upper:
            return False, f"Function '{func}' not allowed in restricted mode"

    return True, ""

@mcp.tool()
def structured_insert(
    table: str,
    data: Dict[str, Any],
    on_conflict: Optional[str] = None,
    returning: Optional[List[str]] = None
) -> str:
    """
    Insert data into a PostgreSQL table using structured parameters with validation.
    
    Args:
        table: Name of the target table
        data: Dictionary of column_name: value pairs to insert
        on_conflict: How to handle conflicts - 'ignore', 'update', or None
        returning: List of column names to return after insert
    
    Returns:
        JSON string with operation result including success status, message, and returned data
    
    Example:
        structured_insert("movies", {"title": "Inception", "release_year": 2010, "rating": 8.8}, returning=["id"])
    """
    try:
        return mcp_insert_tool(table, data, on_conflict, returning, DB_CONFIG)
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error calling insert tool: {str(e)}",
            "inserted_id": None,
            "returning_data": None
        })

@mcp.tool()
def structured_select(
    table: str,
    columns: Optional[List[str]] = None,
    table_alias: Optional[str] = None,
    joins: Optional[List[Dict[str, Any]]] = None,
    where_conditions: Optional[List[Dict[str, Any]]] = None,
    group_by: Optional[List[str]] = None,
    having_conditions: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[List[Dict[str, Any]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    distinct: bool = False
) -> str:
    """
    Select data from PostgreSQL tables using structured parameters with validation.
    
    Args:
        table: Name of the main table to query
        columns: List of column names to select (default: ["*"])
        table_alias: Alias for the main table
        joins: List of join specifications with keys: table, join_type, on_condition, alias
        where_conditions: List of WHERE conditions with keys: column, operator, value, table_alias
        group_by: List of columns for GROUP BY
        having_conditions: List of HAVING conditions
        order_by: List of ordering specifications with keys: column, direction, table_alias
        limit: Maximum number of rows to return
        offset: Number of rows to skip
        distinct: Whether to use SELECT DISTINCT
    
    Returns:
        JSON string with query results including success status, data, and metadata
    
    Example:
        structured_select("movies", columns=["title", "release_year"], 
                         where_conditions=[{"column": "release_year", "operator": ">=", "value": 2000}])
    """
    try:
        return mcp_select_tool(
            table, columns, table_alias, joins, where_conditions,
            group_by, having_conditions, order_by, limit, offset, distinct, DB_CONFIG
        )
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error calling select tool: {str(e)}",
            "data": [],
            "row_count": 0
        })

@mcp.tool()
def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Execute a raw SQL query. Use this for complex queries that cannot be handled 
    by structured_insert or structured_select tools, or for DDL operations.
    
    Args:
        query: SQL query to execute
    
    Returns:
        Dict with query results or execution status
    
    Note:
        For simple INSERT operations, prefer structured_insert for better validation.
        For simple SELECT operations, prefer structured_select for better validation.
    """
    try:
        # Safety check
        is_safe, reason = is_safe_query(query)
        if not is_safe:
            return {
                "success": False,
                "error": f"Query rejected: {reason}"
            }

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Set query timeout
        cursor.execute(f"SET statement_timeout = {QUERY_TIMEOUT * 1000}")

        start_time = time.time()
        cursor.execute(query)
        execution_time = time.time() - start_time

        # Check if it's a SELECT query
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchmany(MAX_ROWS)
            formatted_results = [dict(row) for row in results]
            conn.close()

            return {
                "success": True,
                "data": formatted_results,
                "row_count": len(formatted_results),
                "execution_time_seconds": round(execution_time, 3),
                "limited_to": MAX_ROWS if len(formatted_results) == MAX_ROWS else None,
                "note": "For simple SELECT operations, consider using structured_select for better validation"
            }
        else:
            # For non-SELECT queries
            conn.commit()
            row_count = cursor.rowcount
            conn.close()

            return {
                "success": True,
                "message": f"Query executed successfully. {row_count} rows affected.",
                "row_count": row_count,
                "execution_time_seconds": round(execution_time, 3),
                "note": "For simple INSERT operations, consider using structured_insert for better validation"
            }

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

@mcp.tool()
def list_schemas() -> Dict[str, Any]:
    """List all database schemas available in the PostgreSQL instance."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT schema_name, schema_owner
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name;
        """)
        
        schemas = []
        for row in cursor.fetchall():
            schemas.append({
                "schema_name": row[0],
                "owner": row[1]
            })
        
        conn.close()
        return {
            "success": True,
            "schemas": schemas,
            "count": len(schemas)
        }
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def list_objects(object_type: str = "tables", schema: str = "public") -> Dict[str, Any]:
    """
    List database objects of specified type in a given schema.
    
    Args:
        object_type: Type of objects to list ('tables', 'views', 'indexes', 'sequences', 'functions')
        schema: Schema name (default: 'public')
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if object_type.lower() == "tables":
            cursor.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY table_name;
            """, (schema,))
            
            objects = []
            for row in cursor.fetchall():
                objects.append({
                    "name": row[0],
                    "type": row[1]
                })
                
        elif object_type.lower() == "views":
            cursor.execute("""
                SELECT table_name, view_definition
                FROM information_schema.views
                WHERE table_schema = %s
                ORDER BY table_name;
            """, (schema,))
            
            objects = []
            for row in cursor.fetchall():
                objects.append({
                    "name": row[0],
                    "definition": row[1][:200] + "..." if len(row[1]) > 200 else row[1]
                })
                
        elif object_type.lower() == "indexes":
            cursor.execute("""
                SELECT indexname, tablename, indexdef
                FROM pg_indexes
                WHERE schemaname = %s
                ORDER BY indexname;
            """, (schema,))
            
            objects = []
            for row in cursor.fetchall():
                objects.append({
                    "name": row[0],
                    "table": row[1],
                    "definition": row[2]
                })
                
        else:
            conn.close()
            return {
                "success": False,
                "error": f"Unsupported object type: {object_type}"
            }
        
        conn.close()
        return {
            "success": True,
            "objects": objects,
            "count": len(objects),
            "object_type": object_type,
            "schema": schema
        }
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def get_object_details(object_name: str, object_type: str = "table", schema: str = "public") -> Dict[str, Any]:
    """
    Get detailed information about a specific database object.
    
    Args:
        object_name: Name of the object
        object_type: Type of object ('table', 'view', 'index')
        schema: Schema name (default: 'public')
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if object_type.lower() == "table":
            # Get table columns
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = %s
                ORDER BY ordinal_position;
            """, (object_name, schema))
            
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                    "max_length": row[4]
                })
            
            # Get table constraints
            cursor.execute("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = %s AND table_schema = %s;
            """, (object_name, schema))
            
            constraints = []
            for row in cursor.fetchall():
                constraints.append({
                    "name": row[0],
                    "type": row[1]
                })
            
            conn.close()
            return {
                "success": True,
                "object_name": object_name,
                "object_type": object_type,
                "schema": schema,
                "columns": columns,
                "constraints": constraints
            }
        
        else:
            conn.close()
            return {
                "success": False,
                "error": f"Object type '{object_type}' not yet supported for detailed view"
            }
            
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def explain_query(query: str, analyze: bool = False) -> Dict[str, Any]:
    """
    Get the execution plan for a query using EXPLAIN.
    
    Args:
        query: SQL query to explain
        analyze: Whether to run EXPLAIN ANALYZE (actually executes the query)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        explain_query = f"EXPLAIN {'ANALYZE ' if analyze else ''}(FORMAT JSON) {query}"
        cursor.execute(explain_query)
        
        plan = cursor.fetchone()[0]
        
        conn.close()
        return {
            "success": True,
            "query": query,
            "execution_plan": plan,
            "analyzed": analyze
        }
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def analyze_db_health() -> Dict[str, Any]:
    """Get basic database health metrics and statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Database size
        cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
        db_size = cursor.fetchone()[0]
        
        # Connection count
        cursor.execute("SELECT count(*) FROM pg_stat_activity;")
        connection_count = cursor.fetchone()[0]
        
        # Table count
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]
        
        # Cache hit ratio
        cursor.execute("""
            SELECT round(
                100 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2
            ) as cache_hit_ratio
            FROM pg_stat_database 
            WHERE datname = current_database();
        """)
        cache_hit_ratio = cursor.fetchone()[0]
        
        conn.close()
        return {
            "success": True,
            "database_size": db_size,
            "active_connections": connection_count,
            "table_count": table_count,
            "cache_hit_ratio_percent": float(cache_hit_ratio) if cache_hit_ratio else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def get_slow_queries(limit: int = 10) -> Dict[str, Any]:
    """
    Get slow queries from pg_stat_statements (if extension is available).
    
    Args:
        limit: Number of slow queries to return (default: 10)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if pg_stat_statements is available
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            );
        """)
        
        if not cursor.fetchone()[0]:
            conn.close()
            return {
                "success": False,
                "error": "pg_stat_statements extension is not installed"
            }
        
        cursor.execute(f"""
            SELECT 
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                rows
            FROM pg_stat_statements
            ORDER BY total_exec_time DESC
            LIMIT {limit};
        """)
        
        queries = []
        for row in cursor.fetchall():
            queries.append({
                "query": row[0][:200] + "..." if len(row[0]) > 200 else row[0],
                "calls": row[1],
                "total_time_ms": float(row[2]),
                "avg_time_ms": float(row[3]),
                "rows_affected": row[4]
            })
        
        conn.close()
        return {
            "success": True,
            "slow_queries": queries,
            "count": len(queries)
        }
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def get_table_sizes(schema: str = "public", limit: int = 20) -> Dict[str, Any]:
    """
    Get table sizes ordered by size.
    
    Args:
        schema: Schema to analyze (default: 'public')
        limit: Number of tables to return (default: 20)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT 
                table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size,
                pg_total_relation_size(quote_ident(table_name)) as size_bytes
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC
            LIMIT {limit};
        """, (schema,))
        
        tables = []
        for row in cursor.fetchall():
            tables.append({
                "table_name": row[0],
                "size": row[1],
                "size_bytes": row[2]
            })
        
        conn.close()
        return {
            "success": True,
            "tables": tables,
            "schema": schema,
            "count": len(tables)
        }
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def test_connection() -> Dict[str, Any]:
    """Test the database connection and return connection info."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT version(), current_database(), current_user, inet_server_addr(), inet_server_port();")
        result = cursor.fetchone()
        
        conn.close()
        return {
            "success": True,
            "postgresql_version": result[0],
            "database": result[1],
            "user": result[2],
            "server_address": result[3],
            "server_port": result[4],
            "connection_successful": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "connection_successful": False
        }

@mcp.tool()
def set_server_mode(restricted: bool = True, query_timeout: int = 30, max_rows: int = 1000) -> Dict[str, Any]:
    """
    Configure server safety settings.
    
    Args:
        restricted: Enable restricted mode (blocks dangerous operations)
        query_timeout: Query timeout in seconds
        max_rows: Maximum rows to return per query
    """
    global RESTRICTED_MODE, QUERY_TIMEOUT, MAX_ROWS
    
    RESTRICTED_MODE = restricted
    QUERY_TIMEOUT = max(1, min(300, query_timeout))  # Between 1-300 seconds
    MAX_ROWS = max(1, min(10000, max_rows))  # Between 1-10000 rows
    
    return {
        "success": True,
        "settings": {
            "restricted_mode": RESTRICTED_MODE,
            "query_timeout_seconds": QUERY_TIMEOUT,
            "max_rows_per_query": MAX_ROWS
        }
    }


if __name__ == '__main__':
    # Redirect all startup messages to stderr instead of stdout
    print(f"Starting Enhanced PostgreSQL MCP Server...", file=sys.stderr)
    print(f"Mode: {'Restricted' if RESTRICTED_MODE else 'Unrestricted'}", file=sys.stderr)
    print(f"Query timeout: {QUERY_TIMEOUT}s", file=sys.stderr)
    print(f"Max rows per query: {MAX_ROWS}", file=sys.stderr)
    # print(f"Available tools: structured_insert, structured_select, execute_sql_query, and {len(mcp.list_tools())-3} other tools", file=sys.stderr)
    mcp.run()

