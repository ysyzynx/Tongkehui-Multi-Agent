#!/usr/bin/env python3
"""
为多账号隔离添加 user_id 字段与索引。
支持 PostgreSQL / SQLite。
"""

import os
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import engine  # noqa: E402


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    cols = inspector.get_columns(table_name)
    return any(col.get("name") == column_name for col in cols)


def _safe_exec(conn, sql: str) -> None:
    conn.execute(text(sql))


def migrate(default_user_id: int | None = None) -> None:
    print("=" * 60)
    print("迁移: stories/agent_feedbacks 增加 user_id")
    print("=" * 60)

    dialect = engine.dialect.name
    print(f"数据库类型: {dialect}")

    with engine.connect() as conn:
        inspector = inspect(conn)

        if not _column_exists(inspector, "stories", "user_id"):
            print("[stories] 添加 user_id")
            _safe_exec(conn, "ALTER TABLE stories ADD COLUMN user_id INTEGER")
        else:
            print("[stories] user_id 已存在，跳过")

        if not _column_exists(inspector, "agent_feedbacks", "user_id"):
            print("[agent_feedbacks] 添加 user_id")
            _safe_exec(conn, "ALTER TABLE agent_feedbacks ADD COLUMN user_id INTEGER")
        else:
            print("[agent_feedbacks] user_id 已存在，跳过")

        if default_user_id is not None:
            print(f"回填历史空 user_id -> {default_user_id}")
            _safe_exec(
                conn,
                f"UPDATE stories SET user_id = {int(default_user_id)} WHERE user_id IS NULL",
            )
            _safe_exec(
                conn,
                f"UPDATE agent_feedbacks SET user_id = {int(default_user_id)} WHERE user_id IS NULL",
            )

        # 索引（若不存在）
        if dialect == "postgresql":
            _safe_exec(conn, "CREATE INDEX IF NOT EXISTS ix_stories_user_id ON stories (user_id)")
            _safe_exec(conn, "CREATE INDEX IF NOT EXISTS ix_agent_feedbacks_user_id ON agent_feedbacks (user_id)")
        elif dialect == "sqlite":
            _safe_exec(conn, "CREATE INDEX IF NOT EXISTS ix_stories_user_id ON stories (user_id)")
            _safe_exec(conn, "CREATE INDEX IF NOT EXISTS ix_agent_feedbacks_user_id ON agent_feedbacks (user_id)")

        conn.commit()

    print("迁移完成")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="为 stories/agent_feedbacks 增加 user_id")
    parser.add_argument(
        "--default-user-id",
        type=int,
        default=None,
        help="可选：将历史 user_id 为空的数据回填为该用户ID",
    )
    args = parser.parse_args()
    migrate(default_user_id=args.default_user_id)
