#!/usr/bin/env python3
"""
数据库迁移脚本
为knowledge_documents表添加新字段
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from utils.database import engine


def migrate_database():
    """迁移数据库"""
    print("="*60)
    print("数据库迁移脚本")
    print("="*60)

    with engine.connect() as conn:
        # 检查是否已存在author字段
        result = conn.execute(text("PRAGMA table_info(knowledge_documents)"))
        columns = [row[1] for row in result]

        print(f"\n现有字段: {columns}")

        # 需要添加的字段
        new_columns = [
            ("author", "VARCHAR(255)"),
            ("publish_year", "INTEGER"),
            ("style_tags", "TEXT"),
            ("award_tags", "TEXT"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"\n正在添加字段: {col_name}")
                try:
                    conn.execute(text(f"ALTER TABLE knowledge_documents ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"  ✓ 字段 {col_name} 添加成功")
                except Exception as e:
                    print(f"  ✗ 添加失败: {e}")
            else:
                print(f"\n字段 {col_name} 已存在，跳过")

        # 再次检查
        result = conn.execute(text("PRAGMA table_info(knowledge_documents)"))
        columns = [row[1] for row in result]
        print(f"\n迁移后字段: {columns}")

    print("\n" + "="*60)
    print("数据库迁移完成！")
    print("="*60)


def recreate_database():
    """删除并重建数据库（慎用！）"""
    import shutil

    db_path = "tongkehui.db"
    if os.path.exists(db_path):
        backup_path = "tongkehui.db.backup"
        print(f"正在备份数据库到: {backup_path}")
        shutil.copy(db_path, backup_path)
        print(f"正在删除数据库: {db_path}")
        os.remove(db_path)
        print("数据库已删除，重启服务时会自动重建")
    else:
        print("数据库文件不存在")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("--recreate", action="store_true", help="删除并重建数据库（慎用）")
    args = parser.parse_args()

    if args.recreate:
        confirm = input("警告：这将删除现有数据库！确认吗？(yes/no): ")
        if confirm.lower() == "yes":
            recreate_database()
    else:
        migrate_database()
