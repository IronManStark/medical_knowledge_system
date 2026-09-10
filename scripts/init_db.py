# -*- coding: utf-8 -*-
"""
医学知识库系统 - 数据库初始化脚本
作者：陈的斌
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

MYSQL_CONFIG = {
    'host': os.environ.get('MKS_DB_HOST', '10.211.55.4'),
    'port': int(os.environ.get('MKS_DB_PORT', 3306)),
    'user': os.environ.get('MKS_DB_USER', 'root'),
    'password': os.environ.get('MKS_DB_PASSWORD', ''),
    'database': os.environ.get('MKS_DB_NAME', 'mks'),
    'charset': 'utf8mb4'
}

def execute_sql_file(conn, file_path):
    cursor = conn.cursor()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    sql_statements = sql_content.split(';')
    
    for sql in sql_statements:
        sql = sql.strip()
        if sql and not sql.startswith('--'):
            try:
                cursor.execute(sql)
            except Exception as e:
                print(f"  SQL执行失败: {sql[:50]}... - {e}")
    
    conn.commit()
    cursor.close()
    print("  SQL脚本执行完成")

def main():
    print("=== 医学知识库系统数据库初始化 ===")
    print(f"目标数据库: MySQL ({MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']})")
    print()
    
    if not MYSQL_CONFIG['password']:
        print("警告: 未设置MKS_DB_PASSWORD环境变量")
        return
    
    try:
        conn = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            charset=MYSQL_CONFIG['charset']
        )
        cursor = conn.cursor()
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print("✓ 数据库创建成功")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return
    
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        
        sql_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'init_mysql.sql')
        execute_sql_file(conn, sql_file)
        
        conn.close()
        print("✓ 表结构和初始数据创建成功")
    except Exception as e:
        print(f"✗ 表结构创建失败: {e}")
        return
    
    print()
    print("=== 数据库初始化完成！===")

if __name__ == '__main__':
    main()
