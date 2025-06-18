import psycopg2
from psycopg2.extras import RealDictCursor
import json

def get_all_table_constraints(connection_params, schema_name='public', table_name=None):
    """
    Fetch all constraints defined on a PostgreSQL table including:
    - Primary keys, foreign keys, unique, check constraints
    - Triggers
    - Functions that reference the table
    
    Args:
        connection_params (dict): Database connection parameters
        schema_name (str): Schema name (default: 'public')
        table_name (str): Table name to analyze
    
    Returns:
        dict: Dictionary containing all constraint types
    """
    
    if not table_name:
        raise ValueError("Table name is required")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        constraints_info = {
            'table_name': table_name,
            'schema_name': schema_name,
            'traditional_constraints': [],
            'triggers': [],
            'functions': []
        }
        
        # 1. Get traditional constraints (PK, FK, UNIQUE, CHECK, etc.)
        traditional_constraints_query = """
        SELECT 
            pgc.conname as constraint_name,
            pgc.contype as constraint_type,
            CASE 
                WHEN pgc.contype = 'p' THEN 'PRIMARY KEY'
                WHEN pgc.contype = 'f' THEN 'FOREIGN KEY'
                WHEN pgc.contype = 'u' THEN 'UNIQUE'
                WHEN pgc.contype = 'c' THEN 'CHECK'
                WHEN pgc.contype = 'x' THEN 'EXCLUSION'
                WHEN pgc.contype = 't' THEN 'TRIGGER'
                ELSE 'OTHER'
            END as constraint_type_desc,
            pg_get_constraintdef(pgc.oid) as constraint_definition,
            ccu.table_schema,
            ccu.table_name,
            ccu.column_name
        FROM pg_catalog.pg_constraint pgc
        INNER JOIN pg_catalog.pg_class rel ON rel.oid = pgc.conrelid
        INNER JOIN pg_catalog.pg_namespace nsp ON nsp.oid = pgc.connamespace
        LEFT JOIN information_schema.constraint_column_usage ccu 
            ON pgc.conname = ccu.constraint_name 
            AND nsp.nspname = ccu.constraint_schema
        WHERE nsp.nspname = %s AND rel.relname = %s
        ORDER BY pgc.conname;
        """
        
        cursor.execute(traditional_constraints_query, (schema_name, table_name))
        constraints_info['traditional_constraints'] = [dict(row) for row in cursor.fetchall()]
        
        # 2. Get triggers on the table
        triggers_query = """
        SELECT 
            event_object_schema as table_schema,
            event_object_table as table_name,
            trigger_schema,
            trigger_name,
            string_agg(event_manipulation, ',') as events,
            action_timing as activation,
            action_condition as condition,
            action_statement as definition
        FROM information_schema.triggers
        WHERE event_object_schema = %s AND event_object_table = %s
        GROUP BY 1,2,3,4,6,7,8
        ORDER BY trigger_name;
        """
        
        cursor.execute(triggers_query, (schema_name, table_name))
        constraints_info['triggers'] = [dict(row) for row in cursor.fetchall()]
        
        # 3. Get user-defined functions that might reference the table
        # This searches function definitions for table name references
        functions_query = """
        SELECT 
            n.nspname as function_schema,
            p.proname as function_name,
            pg_get_function_arguments(p.oid) as function_arguments,
            t.typname as return_type,
            l.lanname as function_language,
            CASE 
                WHEN l.lanname = 'internal' THEN p.prosrc
                ELSE pg_get_functiondef(p.oid)
            END as definition
        FROM pg_proc p
        LEFT JOIN pg_namespace n ON p.pronamespace = n.oid
        LEFT JOIN pg_language l ON p.prolang = l.oid
        LEFT JOIN pg_type t ON t.oid = p.prorettype
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND (
            CASE 
                WHEN l.lanname = 'internal' THEN p.prosrc
                ELSE pg_get_functiondef(p.oid)
            END
        ) ~* %s
        ORDER BY function_schema, function_name;
        """
        
        # Search for table name in function definitions (case-insensitive)
        table_pattern = f'\\m{table_name}\\M'
        cursor.execute(functions_query, (table_pattern,))
        constraints_info['functions'] = [dict(row) for row in cursor.fetchall()]
        
        # 4. Get additional constraint information from information_schema
        info_schema_constraints_query = """
        SELECT 
            constraint_name,
            constraint_type,
            table_schema,
            table_name,
            is_deferrable,
            initially_deferred
        FROM information_schema.table_constraints
        WHERE table_schema = %s AND table_name = %s
        ORDER BY constraint_name;
        """
        
        cursor.execute(info_schema_constraints_query, (schema_name, table_name))
        info_schema_constraints = [dict(row) for row in cursor.fetchall()]
        
        # Merge with traditional constraints for complete information
        for constraint in constraints_info['traditional_constraints']:
            for info_constraint in info_schema_constraints:
                if constraint['constraint_name'] == info_constraint['constraint_name']:
                    constraint.update({
                        'is_deferrable': info_constraint['is_deferrable'],
                        'initially_deferred': info_constraint['initially_deferred']
                    })
        
        return constraints_info
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if conn:
            cursor.close()
            conn.close()

def print_constraints_summary(constraints_info):
    """
    Print a formatted summary of all constraints
    """
    if not constraints_info:
        print("No constraint information available")
        return
    
    print(f"\n=== CONSTRAINTS SUMMARY FOR {constraints_info['schema_name']}.{constraints_info['table_name']} ===\n")
    
    # Traditional Constraints
    print("📋 TRADITIONAL CONSTRAINTS:")
    if constraints_info['traditional_constraints']:
        for constraint in constraints_info['traditional_constraints']:
            print(f"  • {constraint['constraint_name']} ({constraint['constraint_type_desc']})")
            print(f"    Definition: {constraint['constraint_definition']}")
            if constraint.get('column_name'):
                print(f"    Column: {constraint['column_name']}")
            print()
    else:
        print("  No traditional constraints found\n")
    
    # Triggers
    print("⚡ TRIGGERS:")
    if constraints_info['triggers']:
        for trigger in constraints_info['triggers']:
            print(f"  • {trigger['trigger_name']}")
            print(f"    Events: {trigger['events']}")
            print(f"    Timing: {trigger['activation']}")
            print(f"    Definition: {trigger['definition']}")
            print()
    else:
        print("  No triggers found\n")
    
    # Functions
    print("🔧 FUNCTIONS REFERENCING TABLE:")
    if constraints_info['functions']:
        for function in constraints_info['functions']:
            print(f"  • {function['function_schema']}.{function['function_name']}")
            print(f"    Arguments: {function['function_arguments']}")
            print(f"    Return Type: {function['return_type']}")
            print(f"    Language: {function['function_language']}")
            print()
    else:
        print("  No functions referencing this table found\n")

# Example usage
if __name__ == "__main__":
    # Database connection parameters
    connection_params = {
        'host': 'localhost',
        'database': 'your_database',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }
    
    # Fetch constraints for a specific table
    table_name = 'your_table_name'
    schema_name = 'public'
    
    constraints = get_all_table_constraints(
        connection_params=connection_params,
        schema_name=schema_name,
        table_name=table_name
    )
    
    if constraints:
        # Print summary
        print_constraints_summary(constraints)
        
        # Save to JSON file
        with open(f'{table_name}_constraints.json', 'w') as f:
            json.dump(constraints, f, indent=2, default=str)
        
        print(f"Detailed constraints saved to {table_name}_constraints.json")
