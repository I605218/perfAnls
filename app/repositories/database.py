"""
数据库连接管理
"""
import asyncpg
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from app.config import get_settings


class Database:
    """数据库连接池管理"""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.settings = get_settings()

    async def connect(self):
        """创建连接池"""
        print(f"🔌 正在连接数据库: {self.settings.database_url}")

        self.pool = await asyncpg.create_pool(
            self.settings.database_url,
            min_size=self.settings.db_pool_min_size,
            max_size=self.settings.db_pool_max_size,
            timeout=self.settings.db_timeout,
        )

        print("✅ 数据库连接池创建成功")

    async def disconnect(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            print("✅ 数据库连接池已关闭")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """获取数据库连接上下文管理器"""
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化，请先调用 connect()")

        async with self.pool.acquire() as connection:
            yield connection


# 全局数据库实例
db = Database()


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    依赖注入函数：获取数据库连接
    用于 FastAPI 的 Depends()
    """
    async with db.get_connection() as conn:
        yield conn
