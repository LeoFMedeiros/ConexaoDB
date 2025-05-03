import psycopg2
from psycopg2 import sql, extras
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis do .env

class PostgresDB:
    def __init__(self):
        """Initialize connection parameters from environment variables."""
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = os.getenv("POSTGRES_PORT", 5432)
        self.dbname = os.getenv("POSTGRES_DB", "mydatabase")
        self.user = os.getenv("POSTGRES_USER", "myuser")
        self.password = os.getenv("POSTGRES_PASSWORD", "mypassword")
        self._conn = None
        self._cur = None

    def _connect(self):
        """Establish connection and create cursor."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            self._conn.autocommit = True # Mantem autocommit se desejado
            self._cur = self._conn.cursor()

    def _close(self):
        """Close cursor and connection if they exist."""
        if self._cur:
            self._cur.close()
            self._cur = None
        if self._conn:
            self._conn.close()
            self._conn = None

    def create_table(self, table_name: str, schema: str):
        """
        Create a table if it doesn't exist.
        Manages connection internally.
        :param table_name: name of the table
        :param schema: column definitions, e.g. "id SERIAL PRIMARY KEY, name TEXT"
        """
        query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
            sql.Identifier(table_name),
            sql.SQL(schema)
        )
        try:
            self._connect()
            self._cur.execute(query)
        finally:
            self._close()

    def execute_query(self, query: str, params: tuple = None):
        """
        Execute a generic SQL command (INSERT/UPDATE/DELETE/...).
        Manages connection internally.
        :param query: SQL string with optional %s placeholders
        :param params: tuple of parameters
        """
        try:
            self._connect()
            self._cur.execute(query, params)
        finally:
            self._close()

    def fetch_all(self, query: str, params: tuple = None) -> list:
        """
        Execute a SELECT and return all rows.
        Manages connection internally.
        :return: list of tuples
        """
        return self.fetch_query(query, params)

    def query(self, query: str, params: tuple = None) -> list:
        """
        Execute a SELECT and return all rows as a list of dictionaries (JSON-like format).
        Manages connection internally.
        :return: list of dictionaries (column_name: value)
        """
        try:
            self._connect()
            # Usamos DictCursor para retornar dados em formato de dicionário
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(query, params)
            result = cur.fetchall()
            cur.close()
            return result
        finally:
            self._close()

    def query_df(self, query: str, params: tuple = None) -> pd.DataFrame:
        """
        Execute a SELECT and return all rows as a pandas DataFrame.
        Manages connection internally.
        :return: pandas DataFrame
        """
        data = self.query(query, params)
        # Converte lista de dicionários para DataFrame
        return pd.DataFrame(data) if data else pd.DataFrame()

    def fetch_query(self, query: str, params: tuple = None) -> list:
        """
        Legacy function. Renamed to query() for new code.
        Execute a SELECT and return all rows.
        Manages connection internally.
        :return: list of tuples
        """
        try:
            self._connect()
            self._cur.execute(query, params)
            result = self._cur.fetchall()
            return result
        finally:
            self._close()

    def delete_data(self, table_name: str, where_clause: str = None):
        """
        Delete data from a table.
        Manages connection internally.
        :param where_clause: optional WHERE condition, e.g. "id > 10"
        """
        if where_clause:
            query = sql.SQL("DELETE FROM {} WHERE {}").format(
                sql.Identifier(table_name),
                sql.SQL(where_clause)
            )
        else:
            query = sql.SQL("DELETE FROM {}").format(sql.Identifier(table_name))
        try:
            self._connect()
            self._cur.execute(query)
        finally:
            self._close()

    def insert_dataframe(self, df: pd.DataFrame, table_name: str):
        """
        Bulk insert a pandas DataFrame into a table.
        Manages connection internally.
        Columns in df must match the table.
        """
        if df.empty:
            print("DataFrame is empty. No data to insert.")
            return

        cols = list(df.columns)
        tuples = [tuple(x) for x in df.to_numpy()]
        query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, cols))
        )
        try:
            self._connect()
            # Use extras.execute_values which handles the connection passed to as_string correctly
            extras.execute_values(self._cur, query.as_string(self._conn), tuples)
        finally:
            self._close()