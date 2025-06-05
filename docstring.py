# Enhanced docstrings for your PostgreSQL MCP server tools
# Total: 9 tools with comprehensive documentation

@mcp.tool()
def execute_sql_query(query: str) -> Dict[str, Any]:
    """Execute a SQL query against the PostgreSQL database with safety checks and performance monitoring.
    
    Supports both SELECT queries (returns data) and DML/DDL operations (INSERT, UPDATE, DELETE, CREATE, etc.).
    In restricted mode, only SELECT queries and safe operations are allowed.
    
    Args:
        query: SQL query string to execute (e.g., "SELECT * FROM users WHERE age > 25")
    
    Returns:
        Dict containing:
        - success: Boolean indicating if query executed successfully
        - data: List of dictionaries with query results (for SELECT queries)
        - row_count: Number of rows returned or affected
        - execution_time_seconds: Query execution time in seconds
        - limited_to: Max rows limit if results were truncated
        - error: Error message if query failed
        - error_type: Type of exception that occurred
    """

@mcp.tool()
def list_schemas() -> Dict[str, Any]:
    """List all available database schemas in the PostgreSQL instance, excluding system schemas.
    
    Retrieves user-created schemas along with their ownership information.
    System schemas (information_schema, pg_catalog, pg_toast) are automatically excluded.
    
    Args:
        None
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - schemas: List of schema objects with 'schema_name' and 'owner' fields
        - count: Total number of schemas found
        - error: Error message if operation failed
    """

@mcp.tool()
def list_objects(schema_name: str = "public") -> Dict[str, Any]:
    """List all database objects within a specified schema including tables, views, sequences, and functions.
    
    Provides a comprehensive inventory of database objects with their types for schema exploration.
    
    Args:
        schema_name: Name of the schema to examine (default: "public")
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - schema: Name of the examined schema
        - objects: List of objects with 'name', 'type' (table/view/sequence/function), and 'full_type' fields
        - count: Total number of objects found
        - error: Error message if operation failed
    """

@mcp.tool()
def get_object_details(object_name: str, schema_name: str = "public") -> Dict[str, Any]:
    """Get comprehensive details about a specific database object including columns, constraints, and indexes.
    
    Provides detailed metadata for tables and views including column specifications, data types,
    constraints (primary keys, foreign keys, unique, check), and index definitions.
    
    Args:
        object_name: Name of the table/view to examine (e.g., "users", "orders")
        schema_name: Schema containing the object (default: "public")
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - object_name: Name of the examined object
        - schema_name: Schema containing the object
        - object_type: Type of object (BASE TABLE, VIEW, etc.)
        - columns: List of column details with data types, nullability, defaults, precision
        - constraints: List of constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)
        - indexes: List of indexes with definitions and tablespace information
        - error: Error message if object not found or operation failed
    """

@mcp.tool()
def explain_query(query: str, analyze: bool = False) -> Dict[str, Any]:
    """Generate execution plan for a SELECT query to analyze performance and optimization opportunities.
    
    Returns PostgreSQL's query execution plan in JSON format. When analyze=True, actually executes
    the query and provides real execution statistics including timing and buffer usage.
    
    Args:
        query: SELECT query to analyze (must start with SELECT for safety)
        analyze: Whether to execute query and gather real statistics (default: False)
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - query: The analyzed query
        - execution_plan: Detailed execution plan in JSON format with costs, nodes, and statistics
        - analyzed: Boolean indicating if real execution statistics were gathered
        - error: Error message if operation failed or query is not SELECT
    """

@mcp.tool()
def analyze_db_health() -> Dict[str, Any]:
    """Perform comprehensive database health analysis including performance metrics and maintenance status.
    
    Analyzes database size, connection statistics, cache performance, index usage, and table maintenance
    status to identify potential performance issues and maintenance needs.
    
    Args:
        None
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - health_report: Comprehensive health analysis including:
            - database_info: Size, name, PostgreSQL version
            - connections: Total, active, idle, and problematic connections
            - cache_performance: Buffer cache hit ratio percentage
            - index_health: Unused indexes that may need removal
            - table_maintenance: Tables with high dead tuple counts needing vacuum/analyze
        - timestamp: When the analysis was performed
        - error: Error message if analysis failed
    """

@mcp.tool()  
def get_slow_queries(limit: int = 5) -> Dict[str, Any]:
    """Retrieve the slowest executing queries from pg_stat_statements for performance optimization.
    
    Requires pg_stat_statements extension to be installed and enabled. Identifies queries
    consuming the most total execution time for optimization opportunities.
    
    Args:
        limit: Maximum number of slow queries to return (default: 5, max recommended: 20)
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - slow_queries: List of queries with performance metrics:
            - query: SQL query text
            - calls: Number of times executed
            - total_time_ms: Total execution time across all calls
            - avg_time_ms: Average execution time per call
            - rows_returned: Average rows returned per execution
            - cache_hit_percent: Buffer cache hit ratio for this query
        - limit: Number of queries requested
        - error: Error message if pg_stat_statements not available or operation failed
    """

@mcp.tool()
def get_table_sizes(schema_name: str = "public", limit: int = 10) -> Dict[str, Any]:
    """Get the largest tables by total size (table data + indexes) within a specified schema.
    
    Helps identify storage usage patterns and tables that might need partitioning or archiving.
    Sizes include both table data and associated indexes.
    
    Args:
        schema_name: Schema to analyze for table sizes (default: "public")
        limit: Maximum number of largest tables to return (default: 10)
    
    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - schema: Name of the analyzed schema
        - tables: List of tables with size information:
            - schema: Schema name
            - table: Table name
            - total_size: Human-readable total size (table + indexes)
            - total_size_bytes: Total size in bytes for sorting/calculations
            - table_size: Human-readable table data size only
            - indexes_size: Human-readable indexes size only
        - count: Number of tables returned
        - error: Error message if operation failed
    """

@mcp.tool()
def test_connection() -> Dict[str, Any]:
    """Test database connectivity and retrieve server configuration information.
    
    Validates database connection and returns comprehensive server information including
    version, connection details, and current server configuration settings.
    
    Args:
        None
    
    Returns:
        Dict containing:
        - success: Boolean indicating connection success
        - message: Success confirmation message
        - server_info: Server details including:
            - postgresql_version: Full PostgreSQL version string
            - database: Current database name
            - user: Connected username
            - server_address: Database server IP address
            - server_port: Database server port
            - database_size_mb: Current database size in megabytes
        - configuration: Current MCP server settings:
            - restricted_mode: Whether dangerous operations are blocked
            - query_timeout: Maximum query execution time in seconds
            - max_rows: Maximum rows returned per SELECT query
        - error: Error message if connection failed
    """

@mcp.tool()
def set_server_mode(restricted: bool = True) -> Dict[str, Any]:
    """Toggle between restricted and unrestricted modes for query execution safety.
    
    Restricted mode blocks potentially dangerous operations (DROP, DELETE, UPDATE, etc.)
    and is recommended for production environments. Unrestricted mode allows all operations.
    
    Args:
        restricted: Whether to enable restricted mode (default: True for safety)
    
    Returns:
        Dict containing:
        - success: Boolean indicating mode change success
        - message: Description of the mode change
        - previous_mode: Previous mode setting ("restricted" or "unrestricted")
        - current_mode: New mode setting ("restricted" or "unrestricted")
    """