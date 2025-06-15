import psycopg2
from typing import Dict, List, Any, Optional, Tuple
import json

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

def validate_columns(schema: Dict[str, Dict], data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate that all columns in data exist in the table schema"""
    errors = []
    
    # Check for non-existent columns
    for column in data.keys():
        if column not in schema:
            similar_cols = [col for col in schema.keys() 
                          if col.lower().replace('_', '') == column.lower().replace('_', '')]
            if similar_cols:
                errors.append(f"Column '{column}' does not exist. Did you mean '{similar_cols[0]}'?")
            else:
                available_cols = list(schema.keys())
                errors.append(f"Column '{column}' does not exist. Available columns: {available_cols}")

    # Check for required columns
    for col_name, col_info in schema.items():
        if (not col_info['nullable'] and 
            col_info['default'] is None and 
            col_name not in data):
            errors.append(f"Column '{col_name}' is required (NOT NULL and no default value)")

    return len(errors) == 0, errors

def build_insert_query(table: str, data: Dict[str, Any], on_conflict: Optional[str],  conflict_target: Optional[List[str]], 
                    update_columns_on_conflict: Optional[List[str]], returning: Optional[List[str]]) -> Tuple[str, List[Any]]:
    """Build a safe parameterized INSERT query"""
    columns = list(data.keys())
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    values = [data[col] for col in columns]

    # Build base query
    query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"

    # Handle conflicts
    if on_conflict == 'ignore':
        query += " ON CONFLICT DO NOTHING"
    elif on_conflict == 'update':
        if not conflict_target:
            raise ValueError("conflict_target is required when on_conflict is 'update'")
        
        # Validate update_columns
        if update_columns_on_conflict is not None:
            invalid_updates = [col for col in update_columns_on_conflict if col not in data]
            if invalid_updates:
                raise ValueError(f"Cannot update columns that were not inserted: {invalid_updates}")
            
        # Choose columns to update (excluding conflict keys by default)
        target_update_cols = update_columns_on_conflict if update_columns_on_conflict is not None else [
            col for col in columns if col not in conflict_target
        ]

        if not target_update_cols:
            raise ValueError("No columns specified to update on conflict.")

        update_assignments = [
            f"{col} = EXCLUDED.{col}" for col in target_update_cols
        ]

        query += f" ON CONFLICT ({', '.join(conflict_target)}) DO UPDATE SET {', '.join(update_assignments)}"

    # Handle RETURNING clause
    if returning:
        returning_cols = ', '.join(returning)
        query += f" RETURNING {returning_cols}"

    return query, values

def mcp_insert_tool(table: str, data: Dict[str, Any], on_conflict: Optional[str] = None, conflict_target: Optional[List[str]]=  None, 
                    update_columns_on_conflict: Optional[List[str]]=  None,
                   returning: Optional[List[str]] = None, db_config: Dict[str, Any] = None) -> str:
    """
    MCP tool for inserting data into PostgreSQL with validation.
    Returns JSON string with operation result.
    """
    try:
        if not db_config:
            return json.dumps({
                'success': False,
                'message': 'Database configuration is required',
                'inserted_id': None,
                'returning_data': None
            })

        with get_connection(db_config) as conn:
            # Validate table exists
            if not validate_table_exists(conn, table):
                return json.dumps({
                    'success': False,
                    'message': f"Table '{table}' does not exist",
                    'inserted_id': None,
                    'returning_data': None
                })

            # Get table schema
            schema = get_table_schema(conn, table)

            # Validate columns
            is_valid, errors = validate_columns(schema, data)
            if not is_valid:
                return json.dumps({
                    'success': False,
                    'message': f"Validation errors: {'; '.join(errors)}",
                    'inserted_id': None,
                    'returning_data': None
                })

            # Build and execute query
            query, values = build_insert_query(table, data, on_conflict, conflict_target, update_columns_on_conflict, returning)
            
            with conn.cursor() as cursor:
                cursor.execute(query, values)

                # Handle returning data
                returning_data = None
                if returning:
                    returning_data = cursor.fetchone()
                    if returning_data:
                        returning_data = dict(zip(returning, returning_data))

                conn.commit()

                return json.dumps({
                    'success': True,
                    'message': f"Successfully inserted 1 row into {table}",
                    'inserted_id': returning_data.get('id') if returning_data and 'id' in returning_data else None,
                    'returning_data': returning_data,
                    'query_executed': query
                })

    except Exception as e:
        return json.dumps({
            'success': False,
            'message': f"Database error: {str(e)}",
            'inserted_id': None,
            'returning_data': None
        })
