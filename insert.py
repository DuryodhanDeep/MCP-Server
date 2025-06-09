import psycopg2
from functools import partial
from collections import namedtuple, defaultdict
from typing import List, Dict, Any, Union, Optional
import textwrap

# Core data structure for representing query parts
_Thing = namedtuple('_Thing', 'alias value is_subquery')
_Thing.__new__.__defaults__ = ('', '', False)

class InsertQueryBuilder:
    """
    A PostgreSQL INSERT query builder focused on batch operations.
    Based on the query builder pattern from death.andgravity.com
    """
    
    # Known SQL keywords and their default separators
    keywords = ['INSERT', 'VALUES', 'ON', 'CONFLICT', 'DO', 'RETURNING']
    separators = {
        'INSERT': ',',
        'VALUES': ',',
        'ON': ' ',
        'CONFLICT': ' ',
        'DO': ' ',
        'RETURNING': ','
    }
    
    # Keywords that always need parentheses
    parens_keywords = {'VALUES'}
    
    # Format strings for different clause types
    alias_formats = defaultdict(lambda: defaultdict(lambda: '{value}'))
    
    def __init__(self, data=None):
        """Initialize the query builder."""
        # Initialize data structure with empty lists for each keyword
        self.data = {keyword: [] for keyword in self.keywords}
        
        # If initial data provided, add it
        if data:
            for keyword, values in data.items():
                if isinstance(values, (list, tuple)):
                    for value in values:
                        self.add(keyword, value)
                else:
                    self.add(keyword, values)
    
    def add(self, keyword, *args):
        """Add arguments to a specific SQL keyword clause."""
        if keyword not in self.data:
            raise KeyError(f"Unknown keyword: {keyword}")
        
        # Clean and convert arguments
        clean_args = []
        for arg in args:
            if isinstance(arg, str):
                # Clean whitespace from string arguments
                clean_arg = textwrap.dedent(arg).strip()
                thing = _Thing.from_arg(clean_arg)
            else:
                # Handle tuples/other types
                thing = _Thing.from_arg(arg)
            clean_args.append(thing)
        
        self.data[keyword].extend(clean_args)
        return self  # Enable method chaining
    
    def __getattr__(self, name):
        """Create SQL keyword methods dynamically (e.g., INSERT, VALUES)."""
        if name.upper() in self.keywords:
            return partial(self.add, name.upper())
        
        # Let parent class handle the AttributeError
        return getattr(super(), name)
    
    def __str__(self):
        """Convert the query to SQL string."""
        return '\n'.join(self._lines())
    
    def _lines(self):
        """Generate formatted SQL lines."""
        for keyword in self.keywords:
            if self.data[keyword]:
                yield from self._lines_keyword(keyword)
    
    def _lines_keyword(self, keyword):
        """Generate lines for a specific keyword clause."""
        values = self.data[keyword]
        if not values:
            return
        
        # Output the keyword
        yield keyword
        
        # Get separator for this keyword
        separator = self.separators.get(keyword, ',')
        
        # Format each value
        for i, thing in enumerate(values):
            # Determine if we need parentheses
            needs_parens = (keyword in self.parens_keywords or 
                          thing.is_subquery)
            
            # Format the value
            if thing.alias:
                # Handle aliased expressions (not common in INSERT but possible)
                formatted = f"{thing.value} AS {thing.alias}"
            else:
                formatted = thing.value
            
            # Add parentheses if needed
            if needs_parens and not (formatted.startswith('(') and formatted.endswith(')')):
                formatted = f"({formatted})"
            
            # Add separator except for last item
            if i < len(values) - 1:
                formatted += f" {separator}"
            
            # Indent the line
            yield self._indent(formatted)
    
    @staticmethod
    def _indent(text, spaces=4):
        """Indent text by specified number of spaces."""
        return ' ' * spaces + text

# Add the from_arg method to _Thing
def _thing_from_arg(cls, arg):
    """Convert various argument types to _Thing namedtuple."""
    if isinstance(arg, cls):
        return arg
    elif isinstance(arg, str):
        return cls('', arg, False)
    elif isinstance(arg, (tuple, list)) and len(arg) == 2:
        alias, value = arg
        return cls(alias, value, False)
    elif isinstance(arg, (tuple, list)) and len(arg) == 3:
        alias, value, is_subquery = arg
        return cls(alias, value, is_subquery)
    else:
        return cls('', str(arg), False)

_Thing.from_arg = classmethod(_thing_from_arg)


class PostgreSQLInsertTool:
    """
    High-level tool for PostgreSQL INSERT operations.
    Handles single inserts, batch inserts, and conflict resolution.
    """
    
    def __init__(self, connection_params: Dict[str, Any]):
        """Initialize with database connection parameters."""
        self.connection_params = connection_params
        self._connection = None
    
    def get_connection(self):
        """Get or create database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(**self.connection_params)
        return self._connection
    
    def close(self):
        """Close database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
    
    def insert_single(self, table: str, data: Dict[str, Any], 
                     on_conflict: Optional[str] = None,
                     returning: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Insert a single row into the specified table.
        
        Args:
            table: Table name
            data: Dictionary of column -> value mappings
            on_conflict: ON CONFLICT clause (e.g., "DO NOTHING", "DO UPDATE SET col = EXCLUDED.col")
            returning: List of columns to return
            
        Returns:
            Dictionary of returned values if returning clause specified
        """
        query = self._build_insert_query(table, [data], on_conflict, returning)
        
        conn = self.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(str(query), list(data.values()))
            
            if returning:
                result = cursor.fetchone()
                if result:
                    return dict(zip(returning, result))
            
            conn.commit()
            return None
    
    def insert_batch(self, table: str, data_list: List[Dict[str, Any]],
                    on_conflict: Optional[str] = None,
                    returning: Optional[List[str]] = None,
                    batch_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Insert multiple rows efficiently using batch operations.
        
        Args:
            table: Table name
            data_list: List of dictionaries with column -> value mappings
            on_conflict: ON CONFLICT clause
            returning: List of columns to return
            batch_size: Number of rows to insert in each batch
            
        Returns:
            List of dictionaries with returned values if returning clause specified
        """
        if not data_list:
            return []
        
        results = []
        conn = self.get_connection()
        
        try:
            # Process in batches
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                
                # Build query for this batch
                query = self._build_insert_query(table, batch, on_conflict, returning)
                
                # Flatten all values for execute
                all_values = []
                for row_data in batch:
                    all_values.extend(row_data.values())
                
                with conn.cursor() as cursor:
                    cursor.execute(str(query), all_values)
                    
                    if returning:
                        batch_results = cursor.fetchall()
                        for result in batch_results:
                            results.append(dict(zip(returning, result)))
            
            conn.commit()
            return results
            
        except Exception as e:
            conn.rollback()
            raise e
    
    def _build_insert_query(self, table: str, data_list: List[Dict[str, Any]],
                           on_conflict: Optional[str] = None,
                           returning: Optional[List[str]] = None) -> InsertQueryBuilder:
        """Build INSERT query using the query builder."""
        if not data_list:
            raise ValueError("data_list cannot be empty")
        
        # Get columns from first row (assume all rows have same structure)
        columns = list(data_list[0].keys())
        
        # Build the query
        query = InsertQueryBuilder()
        
        # INSERT INTO table (columns)
        column_list = ', '.join(columns)
        query.INSERT(f"INTO {table} ({column_list})")
        
        # VALUES clauses - one for each row
        for i, row_data in enumerate(data_list):
            # Create placeholder string for this row
            placeholders = ', '.join(['%s'] * len(columns))
            query.VALUES(placeholders)
        
        # ON CONFLICT clause
        if on_conflict:
            query.ON(f"CONFLICT {on_conflict}")
        
        # RETURNING clause
        if returning:
            query.RETURNING(*returning)
        
        return query


# Example usage and testing
def example_usage():
    """Demonstrate how to use the INSERT query builder."""
    
    # Simple query building
    print("=== Simple INSERT Query ===")
    query = InsertQueryBuilder()
    query.INSERT("INTO users (name, email)").VALUES("(%s, %s)")
    print(query)
    print()
    
    # Batch INSERT
    print("=== Batch INSERT Query ===")
    batch_query = InsertQueryBuilder()
    batch_query.INSERT("INTO users (name, email)")
    batch_query.VALUES("(%s, %s)")
    batch_query.VALUES("(%s, %s)")
    batch_query.VALUES("(%s, %s)")
    print(batch_query)
    print()
    
    # With conflict resolution
    print("=== INSERT with ON CONFLICT ===")
    conflict_query = InsertQueryBuilder()
    conflict_query.INSERT("INTO users (name, email)").VALUES("(%s, %s)")
    conflict_query.ON("CONFLICT (email) DO UPDATE SET name = EXCLUDED.name")
    conflict_query.RETURNING("id", "name")
    print(conflict_query)
    print()
    
    # High-level tool usage example
    print("=== High-level Tool Usage ===")
    
    # Connection parameters (example)
    conn_params = {
        'host': 'localhost',
        'database': 'movies',
        'user': 'username',
        'password': 'password'
    }
    
    # Create tool instance
    insert_tool = PostgreSQLInsertTool(conn_params)
    
    # Example data
    single_movie = {
        'title': 'The Matrix',
        'year': 1999,
        'genre': 'Sci-Fi'
    }
    
    batch_movies = [
        {'title': 'Inception', 'year': 2010, 'genre': 'Sci-Fi'},
        {'title': 'Interstellar', 'year': 2014, 'genre': 'Sci-Fi'},
        {'title': 'The Dark Knight', 'year': 2008, 'genre': 'Action'}
    ]
    
    print("Single insert query would be:")
    single_query = insert_tool._build_insert_query('movies', [single_movie], 
                                                  returning=['id', 'title'])
    print(single_query)
    print()
    
    print("Batch insert query would be:")
    batch_query = insert_tool._build_insert_query('movies', batch_movies,
                                                 on_conflict="(title) DO NOTHING",
                                                 returning=['id'])
    print(batch_query)
    
    # Remember to close connection
    insert_tool.close()

if __name__ == "__main__":
    example_usage()
