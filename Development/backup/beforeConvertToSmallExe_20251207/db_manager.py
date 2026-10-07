# flake8: noqa: E501
# pyright: reportMissingImports=false
# pyright: ignore[reportMissingImports]
# pyright: ignore[reportMissingModuleSource]


import psycopg2
from psycopg2 import pool
import bcrypt
import os
import sys
import logger
from dotenv import load_dotenv
from datetime import datetime, date

# Load environment variables from .env
# load_dotenv()
if getattr(sys, 'frozen', False):
    # Check external location first (next to exe), then bundled location
    exe_dir = os.path.dirname(sys.executable)
    external_env = os.path.join(exe_dir, '.env')
    bundled_env = os.path.join(sys._MEIPASS, '.env')  # pyright: ignore[reportAttributeAccessIssue]
    # Prefer external .env if it exists, otherwise use bundled one
    env_path = external_env if os.path.exists(external_env) else bundled_env
else:
    env_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '.env')  # during dev

logger.logger.info("[db_manager] : Establishing for database connection")
logger.logger.info(f"[db_manager] : env_path = {env_path}")

load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")


# ✅ Create a connection pool
try:
    db_pool = pool.SimpleConnectionPool(
        minconn=1,  # Minimum 1 connection open
        maxconn=10,  # Maximum 10 connections allowed
        # dsn=DATABASE_URL
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host"),
        port=os.getenv("port"),
        dbname=os.getenv("dbname")
    )

    logger.logger.info("[db_manager] : ✅ Database connection pool created successfully.")
except Exception as e:
    logger.logger.exception(f"[db_manager] : ❌ Error creating connection pool: {e}")
    db_pool = None


def connect_db():
    """Retrieve a connection from the pool"""
    if db_pool:
        try:
            return db_pool.getconn()
        except Exception as e:
            logger.logger.exception(f"[db_manager] : ❌ Error getting connection from pool: {e}")
            return None
    else:
        logger.logger.exception("[db_manager] : ❌ Database pool not initialized.")
        return None


def release_connection(conn):
    """Return the connection to the pool"""
    if db_pool and conn:
        db_pool.putconn(conn)


def executionWithRs_query(query, params=None):
    """Execute SELECT queries with proper exception handling"""
    conn = None
    cursor = None
    try:
        conn = connect_db()
        if conn:
            cursor = conn.cursor()

            # # Log final SQL using mogrify for full visibility
            # final_sql1 = cursor.mogrify(query, safe_params(params)).decode('utf-8')
            # final_sql1_clean = " ".join(final_sql1.split())
            # logger.logger.info(f"[db_manager][DEBUG] : executionWithRs_query - Executing SQL => {final_sql1_clean}")

            # Execute query
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            return results

    except psycopg2.Error as db_err:
        logger.logger.exception(f"[db_manager][SQL ERROR] : {str(db_err)}")
        return None

    except Exception as e:
        logger.logger.exception(f"[db_manager][GENERAL ERROR] : {str(e)}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            release_connection(conn)


def executionWithRs_queryWithCommit(query, params=None):
    """Execute SELECT queries with COMMIT and proper exception handling"""
    conn = None
    cursor = None
    try:
        conn = connect_db()
        if conn:
            cursor = conn.cursor()

            # # Log final SQL using mogrify for full visibility
            # final_sql = cursor.mogrify(query, safe_params(params)).decode('utf-8')
            # final_sql_clean = " ".join(final_sql.split())
            # logger.logger.info(f"[db_manager][DEBUG] : executionWithRs_queryWithCommit - Executing SQL => {final_sql_clean}")

            # Execute
            cursor.execute(query, params or ())
            results = cursor.fetchall()

            conn.commit()  # ✅ COMMIT only after success
            return results

    except psycopg2.Error as db_err:
        if conn:
            conn.rollback()  # ✅ Rollback on SQL exception
        logger.logger.exception(f"[db_manager][SQL ERROR] : {str(db_err)}")
        return None

    except Exception as e:
        if conn:
            conn.rollback()  # ✅ Rollback on any other exception
        logger.logger.exception(f"[db_manager][GENERAL ERROR] : {str(e)}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            release_connection(conn)


def execute_query(query, params=None, conn=None):
    """Execute SELECT queries"""
    if conn is None:
        conn = connect_db()  # Only create connection if not passed

    if conn:
        cursor = conn.cursor()

        # # ✅ Print full query before execution
        # if params:
        #     try:
        #         # Log final SQL using mogrify for full visibility
        #         final_sql3 = cursor.mogrify(query, safe_params(params)).decode('utf-8')
        #         final_sql3_clean = " ".join(final_sql3.split())
        #         logger.logger.info(f"[db_manager] : Final SQL => {final_sql3_clean}")
        #     except Exception as e:
        #         logger.logger.warning(f"[db_manager] : Cannot render full SQL : {str(e)}")
        # else:
        #     logger.logger.info(f"[db_manager] : Final SQL = {query}")

        cursor.execute(query, params or ())
        cursor.close()
        """commit and close the connection only each transaction had successfully inserted"""
        # conn.close()
        # if commit:
        #     conn.commit()
    return conn


def commit(conn):
    """Execute SELECT queries"""
    if conn:
        conn.commit()
        conn.close()
        release_connection(conn)  # ✅ Return connection to the pool
    return None


def rollback(conn):
    """Execute SELECT queries"""
    if conn:
        conn.rollback()
        conn.close()
        release_connection(conn)  # ✅ Return connection to the pool
    return None


def hash_password(password):
    """Hash password before storing in DB"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(stored_password, input_password):
    """Verify input password with stored hash"""
    return bcrypt.checkpw(input_password.encode(), stored_password.encode())


def safe_params(params):
    if not params:  # handle None or empty list upfront
        return None

    if isinstance(params, dict):
        # Already named parameters, return as is (let psycopg2 handle named binding)
        return params

    new_params = []
    for p in params:
        if p is None or p == '':
            new_params.append(None)
        elif isinstance(p, datetime):
            new_params.append(p.strftime("%Y-%m-%d %H:%M:%S"))
        elif isinstance(p, date):
            new_params.append(p.strftime("%Y-%m-%d"))
        else:
            new_params.append(p)
    return tuple(new_params)
