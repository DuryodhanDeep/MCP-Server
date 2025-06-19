import psycopg2
import json
from typing import Dict, List, Any


def get_table_constraints(cursor, table_name: str) -> List[Dict[str, Any]]:
    """
    Extract all constraints for a table including:
    - Primary Keys, Foreign Keys, Unique, Check constraints
    - NOT NULL constraints
    - DEFAULT values
    - Triggers
    """
    constraints = []
    
    # Get standard constraints (PK, FK, UNIQUE, CHECK)
    constraints_query = """
        SELECT 
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name,
            cc.check_clause,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name 
            AND tc.table_schema = kcu.table_schema
        LEFT JOIN information_schema.check_constraints cc 
            ON tc.constraint_name = cc.constraint_name
        LEFT JOIN information_schema.constraint_column_usage ccu 
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = %s 
            AND tc.table_schema = 'public'
        ORDER BY tc.constraint_type, tc.constraint_name;
    """
    
    cursor.execute(constraints_query, (table_name,))
    
    for row in cursor.fetchall():
        constraint_name, constraint_type, column_name, check_clause, foreign_table, foreign_column = row
        
        constraint_info = {
            "name": constraint_name,
            "type": constraint_type,
            "column": column_name
        }
        
        # Add specific details based on constraint type
        if constraint_type == 'CHECK' and check_clause:
            constraint_info["check_clause"] = check_clause
        
        if constraint_type == 'FOREIGN KEY':
            constraint_info["references_table"] = foreign_table
            constraint_info["references_column"] = foreign_column
        
        constraints.append(constraint_info)
    
    # Get column-level constraints (NOT NULL, DEFAULT)
    column_info_query = """
        SELECT 
            column_name,
            is_nullable,
            column_default,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_name = %s 
            AND table_schema = 'public'
        ORDER BY ordinal_position;
    """
    
    cursor.execute(column_info_query, (table_name,))
    
    for row in cursor.fetchall():
        column_name, is_nullable, column_default, data_type, char_length, num_precision, num_scale = row
        
        # Add NOT NULL constraints
        if is_nullable == 'NO':
            constraints.append({
                "name": f"{column_name}_not_null",
                "type": "NOT NULL",
                "column": column_name
            })
        
        # Add DEFAULT constraints
        if column_default:
            constraints.append({
                "name": f"{column_name}_default",
                "type": "DEFAULT",
                "column": column_name,
                "default_value": column_default
            })
    
    # Get triggers
    triggers_query = """
        SELECT 
            trigger_name,
            event_manipulation,
            action_timing,
            action_statement
        FROM information_schema.triggers 
        WHERE event_object_table = %s 
            AND event_object_schema = 'public';
    """
    
    cursor.execute(triggers_query, (table_name,))
    
    for row in cursor.fetchall():
        trigger_name, event_manipulation, action_timing, action_statement = row
        constraints.append({
            "name": trigger_name,
            "type": "TRIGGER",
            "event": event_manipulation,
            "timing": action_timing,
            "statement": action_statement
        })
    
    return constraints


def get_column_profiles(cursor, table_name: str) -> List[Dict[str, Any]]:
    """
    Profile each column with:
    - Total values count
    - Distinct values count  
    - Sample of distinct values (up to 20)
    - Data type information
    """
    # Get column information first
    column_info_query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s 
            AND table_schema = 'public'
        ORDER BY ordinal_position;
    """
    
    cursor.execute(column_info_query, (table_name,))
    columns = cursor.fetchall()
    
    column_profiles = []
    
    for column_info in columns:
        column_name = column_info[0]
        data_type = column_info[1]
        
        # Get total count (non-null values)
        total_count_query = f"SELECT COUNT({column_name}) FROM {table_name}"
        cursor.execute(total_count_query)
        total_count = cursor.fetchone()[0]
        
        # Get distinct count
        distinct_count_query = f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name}"
        cursor.execute(distinct_count_query)
        distinct_count = cursor.fetchone()[0]
        
        # Get sample distinct values (handle edge case: less than 20 distinct values)
        sample_limit = min(20, distinct_count)
        sample_values_query = f"""
            SELECT DISTINCT {column_name} 
            FROM {table_name} 
            WHERE {column_name} IS NOT NULL
            ORDER BY RANDOM() 
            LIMIT {sample_limit}
        """
        
        cursor.execute(sample_values_query)
        sample_values = [row[0] for row in cursor.fetchall()]
        
        # Build column profile
        profile = {
            "column_name": column_name,
            "data_type": data_type,
            "total_values": total_count,
            "distinct_values": distinct_count,
            "sample_distinct_values": sample_values
        }
        
        # Add additional type info if available
        if column_info[2]:  # character_maximum_length
            profile["max_length"] = column_info[2]
        if column_info[3]:  # numeric_precision
            profile["numeric_precision"] = column_info[3]
        if column_info[4]:  # numeric_scale
            profile["numeric_scale"] = column_info[4]
        
        column_profiles.append(profile)
    
    return column_profiles


def get_sample_rows(cursor, table_name: str) -> List[Dict[str, Any]]:
    """
    Get random sample rows from table (up to 20 rows)
    Handles edge case where table has fewer than 20 rows
    """
    # First check total row count
    row_count_query = f"SELECT COUNT(*) FROM {table_name}"
    cursor.execute(row_count_query)
    total_rows = cursor.fetchone()[0]
    
    # Get sample rows (limit to available rows if less than 20)
    sample_limit = min(20, total_rows)
    
    if sample_limit == 0:
        return []
    
    sample_rows_query = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {sample_limit}"
    cursor.execute(sample_rows_query)
    
    # Get column names for proper dict formatting
    column_names = [desc[0] for desc in cursor.description]
    
    # Convert rows to list of dictionaries
    sample_rows = []
    for row in cursor.fetchall():
        row_dict = dict(zip(column_names, row))
        sample_rows.append(row_dict)
    
    return sample_rows


def profile_table_tool(connection, table_name: str) -> str:
    """
    Main MCP tool function to get complete table profile
    
    Args:
        connection: PostgreSQL database connection
        table_name: Name of the table to profile
    
    Returns:
        JSON string with comprehensive table analysis including:
        1. All constraints and rules
        2. Column profiling with samples  
        3. Random row samples
    """
    try:
        cursor = connection.cursor()
        
        print(f"Starting table profile for: {table_name}")
        
        # Get all three components
        constraints = get_table_constraints(cursor, table_name)
        column_profiles = get_column_profiles(cursor, table_name)
        sample_rows = get_sample_rows(cursor, table_name)
        
        # Build complete profile
        profile = {
            "table_name": table_name,
            "constraints": constraints,
            "column_profiles": column_profiles,
            "sample_rows": sample_rows,
            "summary": {
                "total_constraints": len(constraints),
                "total_columns": len(column_profiles),
                "sample_rows_count": len(sample_rows)
            }
        }
        
        print(f"Table profile completed for: {table_name}")
        print(f"Found {len(constraints)} constraints, {len(column_profiles)} columns, {len(sample_rows)} sample rows")
        
        return json.dumps(profile, indent=2, default=str)
        
    except Exception as e:
        error_msg = f"Error profiling table {table_name}: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg}, indent=2)
    
    finally:
        if 'cursor' in locals():
            cursor.close()


# Example usage:
# result = profile_table_tool(pg_connection, "movies")
# print(result)
