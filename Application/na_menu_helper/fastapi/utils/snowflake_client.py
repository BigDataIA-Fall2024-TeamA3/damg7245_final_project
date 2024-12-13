# damg7245_final_project/Application/fastapi/utils/snowflake_client.py

import snowflake.connector
import pandas as pd
from config import fastapi_config
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SnowflakeClient:
    def __init__(self):
        try:
            self.conn = snowflake.connector.connect(
                account=fastapi_config.SNOWFLAKE_ACCOUNT,
                user=fastapi_config.SNOWFLAKE_USER,
                password=fastapi_config.SNOWFLAKE_PASSWORD,
                warehouse=fastapi_config.SNOWFLAKE_WAREHOUSE,
                database=fastapi_config.SNOWFLAKE_DATABASE,
                schema=fastapi_config.SNOWFLAKE_SCHEMA,
                role=fastapi_config.SNOWFLAKE_ROLE
            )
            self._ensure_users_table()
            logger.info("Successfully connected to Snowflake and ensured USERS table exists.")
        except snowflake.connector.errors.Error as e:
            logger.error(f"Error connecting to Snowflake: {e}")
            raise

    def close_connection(self):
        if self.conn:
            try:
                self.conn.close()
                logger.info("Snowflake connection closed.")
            except snowflake.connector.errors.Error as e:
                logger.error(f"Error closing Snowflake connection: {e}")

    def _ensure_users_table(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS USERS (
            USERNAME VARCHAR(255) UNIQUE NOT NULL,
            HASHED_PASSWORD VARCHAR(255) NOT NULL
        );
        """
        with self.conn.cursor() as cur:
            cur.execute(create_table_query)
            self.conn.commit()

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        query = "SELECT USERNAME, HASHED_PASSWORD FROM USERS WHERE USERNAME = %s"
        with self.conn.cursor() as cur:
            cur.execute(query, (username,))
            row = cur.fetchone()
            if row:
                return {"username": row[0], "hashed_password": row[1]}
        return None

    def create_user(self, username: str, hashed_password: str):
        insert_query = "INSERT INTO USERS (USERNAME, HASHED_PASSWORD) VALUES (%s, %s)"
        with self.conn.cursor() as cur:
            cur.execute(insert_query, (username, hashed_password))
            self.conn.commit()

