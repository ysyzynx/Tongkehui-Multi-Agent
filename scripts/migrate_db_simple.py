#!/usr/bin/env python3
"""
简单数据库迁移脚本
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from utils.database import engine


def migrate_database():
    print("=== Database Migration ===")

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(knowledge_documents)"))
        columns = [row[1] for row in result]

        print("Existing columns:", columns)

        new_columns = [
            ("author", "VARCHAR(255)"),
            ("publish_year", "INTEGER"),
            ("style_tags", "TEXT"),
            ("award_tags", "TEXT"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                print("Adding column:", col_name)
                try:
                    conn.execute(text(f"ALTER TABLE knowledge_documents ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print("OK")
                except Exception as e:
                    print("Error:", e)
            else:
                print("Column exists:", col_name)

    print("Migration done!")


if __name__ == "__main__":
    migrate_database()
