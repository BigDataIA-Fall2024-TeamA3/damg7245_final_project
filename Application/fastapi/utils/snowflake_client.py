# utils/snowflake_client.py

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
            self._document_info_cache = None  # Initialize cache
            logger.info("Successfully connected to Snowflake.")
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
