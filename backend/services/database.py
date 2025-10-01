"""
Database service for DAT406 Workshop

Manages PostgreSQL connections using psycopg 3 with connection pooling.
Provides async context managers for safe database access.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Any

import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pgvector.psycopg import register_vector

from config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Database connection pool manager for PostgreSQL.
    
    Uses psycopg 3 with async connection pooling for optimal performance.
    Automatically registers pgvector extension for vector operations.
    """
    
    def __init__(self):
        """Initialize database service (pool created on connect)."""
        self._pool: Optional[AsyncConnectionPool] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """
        Initialize database connection pool.
        
        Creates and configures the async connection pool with pgvector support.
        This should be called during application startup.
        
        Raises:
            psycopg.OperationalError: If connection fails
        """
        if self._is_connected:
            logger.warning("Database service already connected")
            return
        
        logger.info("Initializing database connection pool...")
        logger.info(f"Connecting to: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        
        try:
            # Create connection pool
            self._pool = AsyncConnectionPool(
                conninfo=settings.database_url,
                min_size=settings.DB_POOL_MIN_SIZE,
                max_size=settings.DB_POOL_MAX_SIZE,
                timeout=settings.DB_POOL_TIMEOUT,
                open=False,  # Open manually after configuration
                kwargs={
                    "row_factory": dict_row,  # Return rows as dictionaries
                    "autocommit": False,  # Explicit transaction control
                },
                configure=self._configure_connection,
            )
            
            # Open the pool
            await self._pool.open()
            
            # Test connection
            await self._test_connection()
            
            self._is_connected = True
            logger.info(
                f"✅ Database pool initialized "
                f"(min={settings.DB_POOL_MIN_SIZE}, max={settings.DB_POOL_MAX_SIZE})"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _configure_connection(self, conn: AsyncConnection) -> None:
        """
        Configure a new connection from the pool.
        
        Registers pgvector extension for vector operations.
        
        Args:
            conn: New connection to configure
        """
        try:
            # Register pgvector extension
            await register_vector(conn)
            logger.debug("Registered pgvector extension")
            
        except Exception as e:
            logger.error(f"Error configuring connection: {e}")
            raise
    
    async def _test_connection(self) -> None:
        """
        Test database connection and verify pgvector extension.
        
        Raises:
            Exception: If connection test fails
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    # Test basic connectivity
                    await cur.execute("SELECT version();")
                    version = await cur.fetchone()
                    logger.info(f"PostgreSQL version: {version['version'].split(',')[0]}")
                    
                    # Verify pgvector extension
                    await cur.execute(
                        "SELECT * FROM pg_extension WHERE extname = 'vector';"
                    )
                    vector_ext = await cur.fetchone()
                    
                    if vector_ext:
                        logger.info("✅ pgvector extension is available")
                    else:
                        logger.warning("⚠️ pgvector extension not found")
                    
                    # Verify product_catalog table exists
                    await cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'bedrock_integration'
                            AND table_name = 'product_catalog'
                        );
                    """)
                    table_exists = await cur.fetchone()
                    
                    if table_exists and table_exists['exists']:
                        logger.info("✅ product_catalog table found")
                        
                        # Get row count
                        await cur.execute(
                            "SELECT COUNT(*) as count FROM bedrock_integration.product_catalog;"
                        )
                        count_result = await cur.fetchone()
                        logger.info(f"📊 Products in catalog: {count_result['count']:,}")
                    else:
                        logger.warning("⚠️ product_catalog table not found")
                        
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """
        Close database connection pool.
        
        This should be called during application shutdown.
        """
        if self._pool:
            logger.info("Closing database connection pool...")
            await self._pool.close()
            self._is_connected = False
            logger.info("✅ Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[AsyncConnection]:
        """
        Get a database connection from the pool.
        
        Context manager that automatically returns connection to pool.
        
        Yields:
            AsyncConnection: Database connection with dict_row factory
            
        Example:
            ```python
            async with db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT * FROM products")
                    results = await cur.fetchall()
            ```
        
        Raises:
            RuntimeError: If database service not connected
        """
        if not self._is_connected or not self._pool:
            raise RuntimeError(
                "Database service not connected. Call connect() first."
            )
        
        async with self._pool.connection() as conn:
            try:
                yield conn
            except Exception as e:
                # Rollback on error
                await conn.rollback()
                logger.error(f"Database error (rolled back): {e}")
                raise
    
    async def fetch_all(self, query: str, *params: Any) -> list[dict]:
        """
        Execute query and fetch all results.
        
        Args:
            query: SQL query
            *params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchall()
    
    async def fetch_one(self, query: str, *params: Any) -> Optional[dict]:
        """
        Execute query and fetch one result.
        
        Args:
            query: SQL query
            *params: Query parameters
            
        Returns:
            Single result row as dictionary, or None
        """
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchone()
    
    async def execute_query(self, query: str, *params: Any) -> None:
        """
        Execute query without returning results.
        
        Args:
            query: SQL query
            *params: Query parameters
        """
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
    
    async def execute_many(
        self,
        query: str,
        params_list: list[tuple],
    ) -> None:
        """
        Execute a query multiple times with different parameters.
        
        Useful for batch inserts/updates.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
        """
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(query, params_list)
                await conn.commit()
    
    @property
    def is_connected(self) -> bool:
        """Check if database service is connected."""
        return self._is_connected
    
    async def health_check(self) -> dict:
        """
        Check database health status.
        
        Returns:
            dict: Health check results
        """
        if not self._is_connected:
            return {
                "status": "disconnected",
                "error": "Database not connected"
            }
        
        try:
            # Test query
            result = await self.fetch_one("SELECT 1 as test")
            
            # Get pool stats
            pool_stats = {
                "status": "healthy" if result else "unhealthy",
                "pool_size": self._pool.get_stats().pool_size if self._pool else 0,
                "pool_available": self._pool.get_stats().pool_available if self._pool else 0,
            }
            
            return pool_stats
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }