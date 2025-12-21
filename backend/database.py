"""Database utility module for connecting to MySQL and executing queries."""

import mysql.connector
from mysql.connector import Error
from backend import config

def get_db_connection():
    """Create and return a database connection."""
    try:
        connection = mysql.connector.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def execute_query(query, params=None):
    """Execute a query (INSERT, UPDATE, DELETE) and return the cursor."""
    conn = get_db_connection()
    if conn is None:
        return None
    
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor
    except Error as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        # Note: We don't close the cursor here to allow fetching lastrowid if needed,
        # but ideally the caller should handle closing or we use a context manager.
        # For simple scripts, this is okay, but for production, use a pool.
        pass

def execute_batch(query, data_list):
    """Execute a batch insert (executemany) efficiently."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cursor = conn.cursor()
    try:
        cursor.executemany(query, data_list)
        conn.commit()
        print(f"Successfully inserted {cursor.rowcount} rows.")
        return True
    except Error as e:
        print(f"Error executing batch: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def fetch_all(query, params=None):
    """Execute a SELECT query and return all rows."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    cursor = conn.cursor(dictionary=True)
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except Error as e:
        print(f"Error fetching data: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
