#!/usr/bin/env python3
"""
为 users 表增加用户级 LLM 配置字段：
- llm_text_provider
- llm_text_api_key
- llm_image_provider
- llm_image_api_key
"""

import os
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import engine  # noqa: E402


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    cols = inspector.get_columns(table_name)
    return any(col.get("name") == column_name for col in cols)


def migrate() -> None:
    print("=" * 60)
    print("迁移: users 增加用户级 LLM 配置字段")
    print("=" * 60)

    with engine.connect() as conn:
        inspector = inspect(conn)

        if not _column_exists(inspector, "users", "llm_text_provider"):
            conn.execute(text("ALTER TABLE users ADD COLUMN llm_text_provider VARCHAR(32)"))
            print("[users] 添加 llm_text_provider")
        else:
            print("[users] llm_text_provider 已存在")

        if not _column_exists(inspector, "users", "llm_text_api_key"):
            conn.execute(text("ALTER TABLE users ADD COLUMN llm_text_api_key VARCHAR(512)"))
            print("[users] 添加 llm_text_api_key")
        else:
            print("[users] llm_text_api_key 已存在")

        if not _column_exists(inspector, "users", "llm_image_provider"):
            conn.execute(text("ALTER TABLE users ADD COLUMN llm_image_provider VARCHAR(32)"))
            print("[users] 添加 llm_image_provider")
        else:
            print("[users] llm_image_provider 已存在")

        if not _column_exists(inspector, "users", "llm_image_api_key"):
            conn.execute(text("ALTER TABLE users ADD COLUMN llm_image_api_key VARCHAR(512)"))
            print("[users] 添加 llm_image_api_key")
        else:
            print("[users] llm_image_api_key 已存在")

        conn.commit()

    print("迁移完成")


if __name__ == "__main__":
    migrate()
