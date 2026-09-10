# -*- coding: utf-8 -*-
"""
医学知识库系统 - 数据迁移脚本
作者：陈的斌
"""

import os
import sys
import sqlite3
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SQLITE_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'mks.db')

MYSQL_CONFIG = {
    'host': os.environ.get('MKS_DB_HOST', '10.211.55.4'),
    'port': int(os.environ.get('MKS_DB_PORT', 3306)),
    'user': os.environ.get('MKS_DB_USER', 'root'),
    'password': os.environ.get('MKS_DB_PASSWORD', ''),
    'database': os.environ.get('MKS_DB_NAME', 'mks'),
    'charset': 'utf8mb4'
}

BATCH_SIZE = 100

def migrate_table(sqlite_conn, mysql_conn, table_name):
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  {table_name}: 无数据")
        return 0
    
    col_names = [desc[0] for desc in sqlite_cursor.description]
    placeholders = ', '.join(['%s'] * len(col_names))
    col_list = ', '.join(col_names)
    
    sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
    
    try:
        total = len(rows)
        for i in range(0, total, BATCH_SIZE):
            batch = rows[i:i+BATCH_SIZE]
            mysql_cursor.executemany(sql, batch)
            mysql_conn.commit()
        print(f"  {table_name}: {total} 条数据迁移成功")
        return total
    except Exception as e:
        print(f"  {table_name}: 迁移失败 - {e}")
        mysql_conn.rollback()
        return 0
    finally:
        sqlite_cursor.close()
        mysql_cursor.close()

def main():
    print("=== 医学知识库系统数据迁移 ===")
    print(f"源数据库: SQLite ({SQLITE_DB})")
    print(f"目标数据库: MySQL ({MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']})")
    print()
    
    if not MYSQL_CONFIG['password']:
        print("警告: 未设置MKS_DB_PASSWORD环境变量")
        return
    
    if not os.path.exists(SQLITE_DB):
        print(f"✗ SQLite数据库文件不存在: {SQLITE_DB}")
        return
    
    sqlite_conn = None
    mysql_conn = None
    
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        print("✓ SQLite连接成功")
    except Exception as e:
        print(f"✗ SQLite连接失败: {e}")
        return
    
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        print("✓ MySQL连接成功")
    except Exception as e:
        print(f"✗ MySQL连接失败: {e}")
        if sqlite_conn:
            sqlite_conn.close()
        return
    
    tables = [
        'department',
        'role',
        'user',
        'category',
        'knowledge_entry',
        'knowledge_template',
        'model_config',
        'access_log',
        'system_setting'
    ]
    
    total = 0
    for table in tables:
        count = migrate_table(sqlite_conn, mysql_conn, table)
        total += count
    
    if sqlite_conn:
        sqlite_conn.close()
    if mysql_conn:
        mysql_conn.close()
    
    print()
    print(f"=== 迁移完成！共迁移 {total} 条数据 ===")

if __name__ == '__main__':
    main()
