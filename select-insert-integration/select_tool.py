import psycopg2
from typing import Dict, List, Any, Optional, Tuple, Union
import json
from decimal import Decimal
import re


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
    

def get_connection(db_config: Dict[str, Any]):
    """Get a PostgreSQL connection"""
    return psycopg2.connect(**db_config)

def validate_table_exists(conn, table_name: str) -> bool:
    """Check if table exists in the database"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename = %s
                )
            """, (table_name,))
            return cursor.fetchone()[0]
    except Exception as e:
        raise Exception(f"Error checking table existence: {str(e)}")

def get_table_schema(conn, table_name: str) -> Dict[str, Dict[str, Any]]:
    """Get table schema information"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name,))

            schema = {}
            for row in cursor.fetchall():
                col_name, data_type, is_nullable, col_default = row
                schema[col_name] = {
                    'type': data_type,
                    'nullable': is_nullable == 'YES',
                    'default': col_default
                }
            return schema
    except Exception as e:
        raise Exception(f"Error getting table schema: {str(e)}")

def validate_column_reference(col_ref: str, all_schemas: Dict[str, Dict]) -> bool:
    """Validate a column reference, including aggregate functions"""
    
    # Check for aggregate functions
    aggregate_pattern = r'^(COUNT|SUM|AVG|MIN|MAX|STDDEV|VARIANCE)\s*\('
    if re.match(aggregate_pattern, col_ref.upper().strip()):
        # For aggregate functions, validate the column inside parentheses
        # Extract content between parentheses
        match = re.search(r'\((.*?)\)', col_ref)
        if match:
            inner_content = match.group(1).strip()
            # Special case for COUNT(*)
            if inner_content == '*':
                return True
            # Validate the column inside the aggregate function
            return validate_column_reference(inner_content, all_schemas)
        return True  # If we can't parse it, let the database handle it
    
    # Handle column aliases (e.g., "price AS total_price")
    if ' AS ' in col_ref.upper():
        actual_col = col_ref.split(' AS ')[0].strip()
        return validate_column_reference(actual_col, all_schemas)
    
    # Original validation logic for regular columns
    if '.' in col_ref:
        table_part, col_part = col_ref.split('.', 1)
        if table_part in all_schemas:
            return col_part in all_schemas[table_part]
        return False
    else:
        for schema in all_schemas.values():
            if col_ref in schema:
                return True
        return False

def validate_query_structure(conn, table: str, columns: List[str], joins: Optional[List[Dict]] = None) -> Tuple[bool, List[str]]:
    """Validate that all tables and columns exist"""
    errors = []
    all_schemas = {}

    # Get schema for main table
    if not validate_table_exists(conn, table):
        errors.append(f"Table '{table}' does not exist")
        return False, errors

    all_schemas[table] = get_table_schema(conn, table)

    # Get schemas for joined tables
    if joins:
        for join in joins:
            join_table = join.get('table')
            if join_table and not validate_table_exists(conn, join_table):
                errors.append(f"Join table '{join_table}' does not exist")
                continue
            if join_table:
                all_schemas[join_table] = get_table_schema(conn, join_table)

    # Validate SELECT columns
    if columns != ["*"]:
        for col in columns:
            if not validate_column_reference(col, all_schemas):
                errors.append(f"Column '{col}' not found in any table")

    return len(errors) == 0, errors

def build_select_query(table: str, columns: List[str], table_alias: Optional[str] = None,
                      joins: Optional[List[Dict]] = None, where_conditions: Optional[List[Dict]] = None,
                      group_by: Optional[List[str]] = None, having_conditions: Optional[List[Dict]] = None,
                      order_by: Optional[List[Dict]] = None, limit: Optional[int] = None,
                      offset: Optional[int] = None, distinct: bool = False) -> Tuple[str, List[Any]]:
    """Build a safe parameterized SELECT query"""
    query_parts = []
    param_values = []

    # SELECT clause
    distinct_clause = "DISTINCT " if distinct else ""
    columns_str = ", ".join(columns)
    query_parts.append(f"SELECT {distinct_clause}{columns_str}")

    # FROM clause
    from_clause = table
    if table_alias:
        from_clause += f" AS {table_alias}"
    query_parts.append(f"FROM {from_clause}")

    # JOIN clauses
    if joins:
        for join in joins:
            join_type = join.get('join_type', 'INNER JOIN')
            join_table = join['table']
            join_alias = join.get('alias', '')
            on_condition = join['on_condition']
            
            join_clause = f"{join_type} {join_table}"
            if join_alias:
                join_clause += f" AS {join_alias}"
            join_clause += f" ON {on_condition}"
            query_parts.append(join_clause)

    # WHERE clause
    if where_conditions:
        where_clauses = []
        for condition in where_conditions:
            column = condition['column']
            operator = condition['operator']
            value = condition.get('value')
            table_ref = condition.get('table_alias', '')
            
            col_ref = f"{table_ref}.{column}" if table_ref else column
            
            if operator.upper() in ['IS NULL', 'IS NOT NULL']:
                where_clauses.append(f"{col_ref} {operator}")
            elif operator.upper() == 'IN':
                if isinstance(value, list):
                    placeholders = ', '.join(['%s'] * len(value))
                    where_clauses.append(f"{col_ref} IN ({placeholders})")
                    param_values.extend(value)
                else:
                    where_clauses.append(f"{col_ref} IN (%s)")
                    param_values.append(value)
            elif operator.upper() == 'BETWEEN':
                if isinstance(value, list) and len(value) == 2:
                    where_clauses.append(f"{col_ref} BETWEEN %s AND %s")
                    param_values.extend(value)
                else:
                    raise ValueError("BETWEEN operator requires a list of exactly 2 values")
            else:
                where_clauses.append(f"{col_ref} {operator} %s")
                param_values.append(value)

        query_parts.append(f"WHERE {' AND '.join(where_clauses)}")

    # GROUP BY clause
    if group_by:
        query_parts.append(f"GROUP BY {', '.join(group_by)}")
        
        # HAVING clause
        if having_conditions:
            having_clauses = []
            for condition in having_conditions:
                column = condition['column']
                operator = condition['operator']
                value = condition.get('value')
                
                having_clauses.append(f"{column} {operator} %s")
                param_values.append(value)
            
            query_parts.append(f"HAVING {' AND '.join(having_clauses)}")

    # ORDER BY clause
    if order_by:
        order_items = []
        for order in order_by:
            column = order['column']
            direction = order.get('direction', 'ASC')
            table_ref = order.get('table_alias', '')
            
            col_ref = f"{table_ref}.{column}" if table_ref else column
            order_items.append(f"{col_ref} {direction}")
        query_parts.append(f"ORDER BY {', '.join(order_items)}")

    # LIMIT and OFFSET clauses
    if limit is not None:
        query_parts.append(f"LIMIT {limit}")
    if offset is not None:
        query_parts.append(f"OFFSET {offset}")

    return " ".join(query_parts), param_values

def mcp_select_tool(table: str, columns: Optional[List[str]] = None, table_alias: Optional[str] = None,
                   joins: Optional[List[Dict]] = None, where_conditions: Optional[List[Dict]] = None,
                   group_by: Optional[List[str]] = None, having_conditions: Optional[List[Dict]] = None,
                   order_by: Optional[List[Dict]] = None, limit: Optional[int] = None,
                   offset: Optional[int] = None, distinct: bool = False, 
                   db_config: Dict[str, Any] = None) -> str:
    """
    MCP tool for selecting data from PostgreSQL with validation.
    Returns JSON string with query results.
    """
    try:
        if not db_config:
            return json.dumps({
                'success': False,
                'message': 'Database configuration is required',
                'data': [],
                'row_count': 0
            })

        # Set default columns
        if columns is None:
            columns = ["*"]

        with get_connection(db_config) as conn:
            # Validate tables and columns
            is_valid, errors = validate_query_structure(conn, table, columns, joins)
            if not is_valid:
                return json.dumps({
                    'success': False,
                    'message': f"Validation errors: {'; '.join(errors)}",
                    'data': [],
                    'row_count': 0
                })

            # Build and execute query
            query, values = build_select_query(
                table, columns, table_alias, joins, where_conditions,
                group_by, having_conditions, order_by, limit, offset, distinct
            )
            
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                
                # Get column names
                column_names = [desc[0] for desc in cursor.description]
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                data = []
                for row in rows:
                    data.append(dict(zip(column_names, row)))

                return json.dumps({
                    'success': True,
                    'message': f"Successfully retrieved {len(data)} rows",
                    'data': data,
                    'row_count': len(data),
                    'query_executed': query,
                    'columns': column_names
                }, cls=DecimalEncoder)

    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f"Database error: {str(e)}",
            'data': [],
            'row_count': 0
        }, cls=DecimalEncoder)
