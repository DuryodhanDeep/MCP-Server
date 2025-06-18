#!/usr/bin/env python3
"""
MCP Tool for fetching comprehensive PostgreSQL database constraints including 
those defined by functions, triggers, check constraints, foreign keys, and more.
"""

import json
import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ConstraintInfo:
    """Data class representing a database constraint"""
    constraint_name: str
    constraint_type: str
    table_name: str
    column_names: List[str]
    definition: str
    referenced_table: Optional[str] = None
    referenced_columns: Optional[List[str]] = None
    update_rule: Optional[str] = None
    delete_rule: Optional[str] = None
    check_clause: Optional[str] = None
    source_type: str = "DIRECT"  # DIRECT, TRIGGER, FUNCTION


class PostgreSQLConstraintExtractor:
    """PostgreSQL constraint extractor"""
    
    def __init__(self, connection_params: Dict[str, Any]):
        self.connection = psycopg2.connect(**connection_params)
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    def get_table_constraints(self, table_name: str, schema: str = 'public') -> List[ConstraintInfo]:
        """Get all direct constraints for a table"""
        query = """
        SELECT 
            tc.constraint_name,
            tc.constraint_type,
            tc.table_name,
            array_agg(kcu.column_name ORDER BY kcu.ordinal_position) as column_names,
            CASE 
                WHEN tc.constraint_type = 'FOREIGN KEY' THEN ccu.table_name
                ELSE NULL
            END as referenced_table,
            CASE 
                WHEN tc.constraint_type = 'FOREIGN KEY' THEN array_agg(ccu.column_name ORDER BY kcu.ordinal_position)
                ELSE NULL
            END as referenced_columns,
            rc.update_rule,
            rc.delete_rule,
            cc.check_clause,
            pg_get_constraintdef(pgc.oid) as definition
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name 
            AND tc.table_schema = kcu.table_schema
        LEFT JOIN information_schema.constraint_column_usage ccu 
            ON tc.constraint_name = ccu.constraint_name 
            AND tc.table_schema = ccu.table_schema
        LEFT JOIN information_schema.referential_constraints rc 
            ON tc.constraint_name = rc.constraint_name 
            AND tc.table_schema = rc.constraint_schema
        LEFT JOIN information_schema.check_constraints cc 
            ON tc.constraint_name = cc.constraint_name 
            AND tc.table_schema = cc.constraint_schema
        LEFT JOIN pg_constraint pgc 
            ON tc.constraint_name = pgc.conname
        WHERE tc.table_name = %s AND tc.table_schema = %s
        GROUP BY tc.constraint_name, tc.constraint_type, tc.table_name, 
                 ccu.table_name, rc.update_rule, rc.delete_rule, cc.check_clause, pgc.oid
        """
        
        self.cursor.execute(query, (table_name, schema))
        rows = self.cursor.fetchall()
        
        constraints = []
        for row in rows:
            constraints.append(ConstraintInfo(
                constraint_name=row['constraint_name'],
                constraint_type=row['constraint_type'],
                table_name=row['table_name'],
                column_names=row['column_names'] or [],
                definition=row['definition'] or '',
                referenced_table=row['referenced_table'],
                referenced_columns=row['referenced_columns'],
                update_rule=row['update_rule'],
                delete_rule=row['delete_rule'],
                check_clause=row['check_clause']
            ))
        
        return constraints
    
    def get_trigger_constraints(self, table_name: str, schema: str = 'public') -> List[ConstraintInfo]:
        """Get constraints enforced by triggers"""
        query = """
        SELECT 
            t.trigger_name,
            t.event_object_table as table_name,
            pg_get_triggerdef(pg_trigger.oid) as definition,
            t.action_timing,
            t.event_manipulation,
            t.action_statement
        FROM information_schema.triggers t
        LEFT JOIN pg_trigger ON pg_trigger.tgname = t.trigger_name
        WHERE t.event_object_table = %s 
            AND t.event_object_schema = %s
            AND t.trigger_name NOT LIKE 'RI_%%'  -- Exclude system FK triggers
        """
        
        self.cursor.execute(query, (table_name, schema))
        rows = self.cursor.fetchall()
        
        constraints = []
        for row in rows:
            constraints.append(ConstraintInfo(
                constraint_name=row['trigger_name'],
                constraint_type='TRIGGER',
                table_name=row['table_name'],
                column_names=[],
                definition=row['definition'] or row['action_statement'],
                source_type="TRIGGER"
            ))
        
        return constraints
    
    def get_function_constraints(self, table_name: str, schema: str = 'public') -> List[ConstraintInfo]:
        """Get constraints enforced by functions that reference this table"""
        query = """
        SELECT DISTINCT
            p.proname,
            %s as table_name,
            pg_get_functiondef(p.oid) as definition
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = %s
            AND pg_get_functiondef(p.oid) ILIKE %s
            AND p.prokind = 'f'
        """
        
        table_pattern = f'%{table_name}%'
        
        self.cursor.execute(query, (table_name, schema, table_pattern))
        rows = self.cursor.fetchall()
        
        constraints = []
        for row in rows:
            constraints.append(ConstraintInfo(
                constraint_name=row['proname'],
                constraint_type='FUNCTION',
                table_name=row['table_name'],
                column_names=[],
                definition=row['definition'],
                source_type="FUNCTION"
            ))
        
        return constraints
    
    def get_all_constraints(self, table_name: str, schema: str = 'public') -> List[ConstraintInfo]:
        """Get all constraints for a table"""
        constraints = []
        
        # Get direct constraints
        constraints.extend(self.get_table_constraints(table_name, schema))
        
        # Get trigger constraints
        constraints.extend(self.get_trigger_constraints(table_name, schema))
        
        # Get function constraints
        constraints.extend(self.get_function_constraints(table_name, schema))
        
        return constraints
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


def fetch_database_constraints(
    connection_params: Dict[str, Any],
    table_name: str,
    schema: str = 'public'
) -> str:
    """
    MCP tool entry point for fetching PostgreSQL database constraints
    
    Args:
        connection_params: PostgreSQL connection parameters
        table_name: Name of the table
        schema: Schema name (default: 'public')
    
    Returns:
        JSON string with constraint information
    
    Usage:
        fetch_database_constraints(
            {'host': 'localhost', 'database': 'mydb', 'user': 'user', 'password': 'pass'},
            'users'
        )
    """
    
    extractor = None
    try:
        extractor = PostgreSQLConstraintExtractor(connection_params)
        constraints = extractor.get_all_constraints(table_name, schema)
        
        # Group constraints by type
        grouped_constraints = {}
        for constraint in constraints:
            constraint_type = constraint.constraint_type
            if constraint_type not in grouped_constraints:
                grouped_constraints[constraint_type] = []
            grouped_constraints[constraint_type].append(asdict(constraint))
        
        result = {
            'database_type': 'postgresql',
            'table_name': table_name,
            'schema': schema,
            'total_constraints': len(constraints),
            'constraints_by_type': grouped_constraints,
            'all_constraints': [asdict(c) for c in constraints]
        }
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'table_name': table_name,
            'schema': schema
        }, indent=2)
    
    finally:
        if extractor:
            extractor.close()


# Example usage
if __name__ == "__main__":
    # Example connection parameters
    conn_params = {
        'host': 'localhost',
        'database': 'testdb',
        'user': 'postgres',
        'password': 'password'
    }
    
    # Get all constraints for a table
    result = fetch_database_constraints(conn_params, 'users')
    print(result)
