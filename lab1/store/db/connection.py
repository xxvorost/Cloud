import os
import sys
import mysql.connector
from mysql.connector import pooling

# НЕ створюємо pool при імпорті
_connection_pool = None


def create_connection_pool():
    """Create database connection pool with Cloud Run support"""
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "myuser")
    db_name = os.environ.get("DB_NAME", "mydb")
    
    # Debug logging - це з'явиться в Cloud Run logs
    print(f"=== Database Configuration Debug ===", file=sys.stderr)
    print(f"DB_HOST: {db_host}", file=sys.stderr)
    print(f"DB_USER: {db_user}", file=sys.stderr)
    print(f"DB_NAME: {db_name}", file=sys.stderr)
    print(f"DB_PASSWORD present: {bool(os.environ.get('DB_PASSWORD'))}", file=sys.stderr)
    print(f"===================================", file=sys.stderr)
    
    # Check if using Cloud SQL unix socket
    if db_host.startswith("/cloudsql/"):
        connection_config = {
            "unix_socket": db_host, 
            "user": db_user,
            "password": os.environ.get("DB_PASSWORD", "mypassword"),
            "database": db_name,
            "pool_name": "mypool",
            "pool_size": 5,
            "pool_reset_session": True,
        }
        print(f"Using unix socket: {db_host}", file=sys.stderr)
    else:
        connection_config = {
            "host": db_host,
            "user": db_user,
            "password": os.environ.get("DB_PASSWORD", "mypassword"),
            "database": db_name,
            "port": int(os.environ.get("DB_PORT", 3306)),
            "pool_name": "mypool",
            "pool_size": 5,
            "pool_reset_session": True,
        }
        print(f"Using TCP connection: {db_host}:{os.environ.get('DB_PORT', 3306)}", file=sys.stderr)
    
    try:
        pool = pooling.MySQLConnectionPool(**connection_config)
        print(f"✓ Database connection pool created successfully", file=sys.stderr)
        return pool
    except Exception as e:
        print(f"✗ Error creating connection pool: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def get_db_connection():
    """Get connection from pool with lazy initialization and automatic retry"""
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = create_connection_pool()
    
    if _connection_pool is None:
        raise Exception("Database connection pool is not available")
    
    try:
        return _connection_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error getting connection from pool: {err}")
        # Try to recreate pool if it's broken
        _connection_pool = create_connection_pool()
        if _connection_pool is None:
            raise Exception("Failed to recreate connection pool")
        return _connection_pool.get_connection()


db_connection = None
